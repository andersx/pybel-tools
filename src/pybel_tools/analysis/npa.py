"""

An variant of the Network Pertubation Amplitude algorithm inspired by Reagon Kharki's implementation

"""

from __future__ import print_function

import logging
import random
from operator import itemgetter

from pybel.canonicalize import calculate_canonical_name
from pybel.constants import RELATION, CAUSAL_DECREASE_RELATIONS, CAUSAL_INCREASE_RELATIONS, BIOPROCESS
from ..selection.induce_subgraph import get_upstream_causal_subgraph
from ..selection.utils import get_nodes_by_function

__all__ = [
    'NPA_SCORE',
    'DEFAULT_SCORE',
    'run_on_upstream_of_bioprocess',
    'run',
]

log = logging.getLogger(__name__)

#: Signifies the NPA score in the node's data dictionary
NPA_SCORE = 'score'

#: The default score for NPA
DEFAULT_SCORE = 999.99


# TODO implement
def calculate_average_npa_by_annotation(graph, key, annotation='Subgraph'):
    """For each subgraph induced over the edges matching the annotation, calculate the average NPA score
    for all of the contained biological processes

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param key: The key in the node data dictionary representing the experimental data
    :type key: str
    :param annotation: A BEL annotation
    :type annotation: str
    """
    raise NotImplementedError


def run_on_upstream_of_bioprocess(graph, key):
    """Runs NPA on graphs constrained to be strictly one element upstream of biological processes.
    This function can be later extended to go back multiple levels.

    1. Get all biological processes
    2. Get subgraphs induced one level back from each biological process
    3. NPA on each induced subgraph

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param key: The key in the node data dictionary representing the experimental data
    :type key: str
    :return: A dictionary of {node: upstream causal subgraph}
    :rtype: dict
    """

    nodes = list(get_nodes_by_function(graph, BIOPROCESS))

    sgs = {node: get_upstream_causal_subgraph(graph, node) for node in nodes}

    for sg in sgs.values():
        run(sg, key=key)

    return sgs


def run(graph, key, initial_score=DEFAULT_SCORE):
    """

    Nodes that don't have any predecessors can be calculated directly

    1. For nodes without predecessors, their differential gene expression score is assigned as their NPA score
    2. All nodes with predecessors

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param key: The key in the node data dictionary representing the experimental data
    :type key: str
    """

    all_hubs = set()

    for node in graph.nodes_iter():
        if not graph.predecessors(node):
            graph.node[node][NPA_SCORE] = graph.node[node].get(key, 0)
        else:
            graph.node[node][NPA_SCORE] = initial_score
            all_hubs.add(node)

    hub_list = list(all_hubs)

    iteration_count = 0

    while hub_list:

        iteration_count += 1

        log.info('Iteration %s', iteration_count)

        remove = set()

        for node in hub_list:
            log.info('investigating node: %s', calculate_canonical_name(graph, node))

            # if this hub only has upstream not-hubs, then calculate its score based on them and remove from hub list
            if all(predecessor not in all_hubs for predecessor in graph.predecessors(node)):
                graph.node[node][NPA_SCORE] = calculate_npa_score_iteration(graph, node)
                remove.add(node)
                log.info('removing node: %s', calculate_canonical_name(graph, node))

        hub_list = [node for node in hub_list if node not in remove]
        log.info('remove list: %s', remove)

        if not remove:  # all previous hubs in the list have been considered
            get_score_central_hub(graph, all_hubs, hub_list, key)
            return


def get_score_central_hub(graph, all_hubs, hub_list, key, recur_limit=20):
    """Recursively scores central hubs

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param all_hubs: set
    :type hub_list: list
    :param key: The key in the node data dictionary representing the experimental data
    :type key: str
    """
    if not hub_list or recur_limit == 0:
        return

    log.info('scoring hub list: %s', hub_list)
    new_hub_list = []

    for node in hub_list:
        if any(graph.node[predecessor][NPA_SCORE] == DEFAULT_SCORE for predecessor in graph.predecessors_iter(node)):
            new_hub_list.append(node)
        else:
            graph.node[node][NPA_SCORE] = calculate_npa_score_iteration(graph, node)

    get_score_central_hub(graph, all_hubs, new_hub_list, key, recur_limit - 1)


def calculate_npa_score_iteration(graph, node):
    """Calculates the score of the given node

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param node: A node in the BEL graph
    :type node: tuple
    :return: The new score of the node
    :rtype: float
    """
    score = graph.node[node][NPA_SCORE] if NPA_SCORE in graph.node[node] else DEFAULT_SCORE

    for predecessor, _, d in graph.in_edges_iter(node, data=True):
        if d[RELATION] in CAUSAL_INCREASE_RELATIONS:
            score += graph.node[predecessor][NPA_SCORE]
        elif d[RELATION] in CAUSAL_DECREASE_RELATIONS:
            score -= graph.node[predecessor][NPA_SCORE]

    return score


class NpaRunner:
    def __init__(self, graph, key):
        """

        :param graph: A BEL graph
        :type graph: pybel.BELGraph
        :param key:
        :param initial_score:
        """

        self.graph = graph.copy()
        self.key = key

        self.all_hubs = set()

        for node, data in self.graph.nodes_iter(data=True):
            if not self.graph.predecessors(node):
                self.graph.node[node][NPA_SCORE] = data.get(key, 0)
                log.debug('initializing %s with %s', node, self.graph.node[node][NPA_SCORE])
            else:
                self.all_hubs.add(node)

        self.hub_list = list(self.all_hubs)

    def iter_unscored(self):
        for n, d in self.graph.nodes_iter(data=True):
            if NPA_SCORE not in d:
                yield n

    def iter_leaves(self):
        """Returns an iterable over all leaves

        What makes a leaf?

        A node is a leaf if:
         - it doesn't have any predecessors, OR
         - all of its predecessors have NPA score in their data dictionaries

        :return:
        """
        for n in self.graph.nodes_iter():

            if NPA_SCORE in self.graph.node[n]:
                continue

            if not any(NPA_SCORE not in self.graph.node[p] for p in self.graph.predecessors_iter(n)):
                yield n

    def in_out_ratio(self, node):
        return self.graph.in_degree(node) / float(self.graph.out_degree(node))

    def remove_random_edge(self):
        """This function should be run when there are no leaves, but there are still unscored nodes. It will introduce
        a probabilistic element to the algorithm, where some edges are disregarded randomly to eventually get a score
        for the network. This means that the NPA score can be averaged over many runs for a given graph, and a better
        data structure will have to be later developed that doesn't destroy the graph (instead, annotates which edges
        have been disregarded, later)

           1. get all unscored
           2. rank by in-degree
           3. weighted probability over all in-edges where lower in-degree means higher probability
           4. pick randomly which edge
        """

        nodes = [(n, self.in_out_ratio(n)) for n, d in self.graph.nodes_iter(data=True) if NPA_SCORE not in d]
        node, deg = min(nodes, key=itemgetter(1))
        log.debug('checking %s with in/out ratio: %s', node, deg)
        edge_to_remove = random.sample(self.graph.in_edges(node, keys=True), 1)
        self.graph.remove_edge(*edge_to_remove)

    def remove_random_edge_until_has_leaves(self):
        while True:
            leaves = set(self.iter_leaves())
            if leaves:
                return
            self.remove_random_edge()

    def chomp_leaves(self):
        leaves = set(self.iter_leaves())

        if not leaves:
            # this means that there still are some unscored, so choose a random one that has minimal number of in
            # edges, and disregard those in-edges

            """
            1. get all unscored
            2. rank by in-degree
            3. weighted probability over all in-edges where lower in-degree means higher probability
            4. pick randomly which edge

            """

            leaf = random.sample(set(self.iter_unscored()), 1)
            log.warning('no leaves. randomly chose: %s', leaf)
            leaves = [leaf]

        for leaf in leaves:
            self.graph.node[leaf][NPA_SCORE] = calculate_npa_score_iteration(self.graph, leaf)
            log.debug('chomping %s', leaf)

    def get_remaining_graph(self):
        return self.graph.subgraph(n for n, d in self.graph.nodes_iter(data=True) if NPA_SCORE not in d)
