# -*- coding: utf-8 -*-

"""

An variant of the Network Pertubation Amplitude algorithm

"""

from __future__ import print_function

import logging
import random
from operator import itemgetter

from pybel.constants import BIOPROCESS
from pybel.constants import RELATION, CAUSAL_DECREASE_RELATIONS, CAUSAL_INCREASE_RELATIONS
from ..generation import generate_mechanism
from ..selection.utils import get_nodes_by_function

__all__ = [
    'NpaRunner',
    'multirun',
    'multirun_average',
    'workflow',
    'workflow_all',
    'workflow_all_average',
]

log = logging.getLogger(__name__)

#: Signifies the NPA score in the node's data dictionary
NPA_SCORE = 'score'

#: The default score for NPA
DEFAULT_SCORE = 0


class NpaRunner:
    def __init__(self, graph, target_node, key, tag=None, default_score=None):
        """Initializes the NPA runner class

        :param graph: A BEL graph
        :type graph: pybel.BELGraph
        :param target_node: The BEL node that is the focus of this analysis
        :type target_node: tuple
        :param key: The key for the nodes' data dictionaries that points to their original experimental measurements
        :type key: str
        :param tag: The key for the nodes' data dictionaries where the NPA scores will be put. Defaults to 'score'
        :type tag: str
        :param default_score: The initial NPA score for all nodes. This number can go up or down.
        :type default_score: float
        """

        self.graph = graph.copy()
        self.target_node = target_node
        self.key = key

        self.default_score = DEFAULT_SCORE if default_score is None else default_score
        self.tag = NPA_SCORE if tag is None else tag

        for node, data in self.graph.nodes_iter(data=True):
            if not self.graph.predecessors(node):
                self.graph.node[node][self.tag] = data.get(key, 0)
                log.debug('initializing %s with %s', target_node, self.graph.node[node][self.tag])

    def iter_leaves(self):
        """Returns an iterable over all nodes that are leaves. A node is a leaf if either:

         - it doesn't have any predecessors, OR
         - all of its predecessors have NPA score in their data dictionaries

        :return: An iterable over all leaf nodes
        :rtype: iter
        """
        for node in self.graph.nodes_iter():
            if self.tag in self.graph.node[node]:
                continue

            if not any(self.tag not in self.graph.node[p] for p in self.graph.predecessors_iter(node)):
                yield node

    def has_leaves(self):
        """Returns if the current graph has any leaves.

        Implementation is not that smart currently, and does a full sweep.

        :return: Does the current graph have any leaves?
        :rtype: bool
        """
        leaves = list(self.iter_leaves())
        return leaves

    def in_out_ratio(self, node):
        """Calculates the ratio of in-degree / out-degree of a node

        :param node: A BEL node
        :type node: tuple
        :return: The in-degree / out-degree ratio for the given node
        :rtype: float
        """
        return self.graph.in_degree(node) / float(self.graph.out_degree(node))

    def unscored_nodes_iter(self):
        """Iterates over all nodes without a NPA score"""
        for node, data in self.graph.nodes_iter(data=True):
            if self.tag not in data:
                yield node

    def get_random_edge(self):
        """This function should be run when there are no leaves, but there are still unscored nodes. It will introduce
        a probabilistic element to the algorithm, where some edges are disregarded randomly to eventually get a score
        for the network. This means that the NPA score can be averaged over many runs for a given graph, and a better
        data structure will have to be later developed that doesn't destroy the graph (instead, annotates which edges
        have been disregarded, later)

           1. get all unscored
           2. rank by in-degree
           3. weighted probability over all in-edges where lower in-degree means higher probability
           4. pick randomly which edge


        :return: A random in-edge to the lowest in/out degree ratio node. This is a 3-tuple of (node, node, key)
        :rtype: tuple
        """
        nodes = [(n, self.in_out_ratio(n)) for n in self.unscored_nodes_iter() if n != self.target_node]
        node, deg = min(nodes, key=itemgetter(1))
        log.log(5, 'checking %s (in/out ratio: %.3f)', node, deg)

        possible_edges = self.graph.in_edges(node, keys=True)
        log.log(5, 'possible edges: %s', possible_edges)

        edge_to_remove = random.choice(possible_edges)
        log.log(5, 'chose: %s', edge_to_remove)

        return edge_to_remove

    def remove_random_edge(self):
        """Removes a random in-edge from the node with the lowest in/out degree ratio"""
        u, v, k = self.get_random_edge()
        log.debug('removing %s, %s (%s)', u, v, k)
        self.graph.remove_edge(u, v, k)

    def remove_random_edge_until_has_leaves(self):
        """Removes random edges until there is at least one leaf node"""
        while True:
            leaves = set(self.iter_leaves())
            if leaves:
                return
            self.remove_random_edge()

    def score_leaves(self):
        """Calculates the NPA score for all leaves

        :return: The set of leaf nodes that were scored
        :rtype: set
        """
        leaves = set(self.iter_leaves())

        if not leaves:
            log.warning('no leaves.')
            return set()

        for leaf in leaves:
            self.graph.node[leaf][self.tag] = self.calculate_score(leaf)
            log.debug('chomping %s', leaf)

        return leaves

    def run(self):
        """Calculates NPA scores for all leaves until there are none, removes edges until there are, and repeats until
        all nodes have been scored
        """
        while not self.done_chomping():
            self.remove_random_edge_until_has_leaves()
            self.score_leaves()

    def run_with_graph_transformation(self):
        """Calculates NPA scores for all leaves until there are none, removes edges until there are, and repeats until
        all nodes have been scored. Also, yields the current graph at every step so you can make a cool animation
        of how the graph changes throughout the course of the algorithm

        :return: An iterable of BEL graphs
        :rtype: iter
        """
        yield self.get_remaining_graph()
        while not self.done_chomping():
            while not list(self.iter_leaves()):
                self.remove_random_edge()
                yield self.get_remaining_graph()
            self.score_leaves()
            yield self.get_remaining_graph()

    def done_chomping(self):
        """Determines if the algorithm is complete by checking if the target node of this analysis has been scored
        yet. Because the algorithm removes edges when it gets stuck until it is un-stuck, it is always guaranteed to
        finish.

        :return: Is the algorithm done running?
        :rtype: bool
        """
        return self.tag in self.graph.node[self.target_node]

    def get_final_score(self):
        """Returns the final score for the target node

        :return: The final score for the target node
        :rtype: float
        """
        if not self.done_chomping():
            raise ValueError('Algorithm has not completed')

        return self.graph.node[self.target_node][self.tag]

    def calculate_score(self, node):
        """Calculates the score of the given node

        :param node: A node in the BEL graph
        :type node: tuple
        :return: The new score of the node
        :rtype: float
        """
        score = self.graph.node[node][self.tag] if self.tag in self.graph.node[node] else self.default_score

        for predecessor, _, d in self.graph.in_edges_iter(node, data=True):
            if d[RELATION] in CAUSAL_INCREASE_RELATIONS:
                score += self.graph.node[predecessor][self.tag]
            elif d[RELATION] in CAUSAL_DECREASE_RELATIONS:
                score -= self.graph.node[predecessor][self.tag]

        return score

    def get_remaining_graph(self):
        """Allows for introspection on the algorithm at a given point by returning the subgraph induced
        by all unscored nodes

        :return: The remaining unscored BEL graph
        :rtype: pybel.BELGraph
        """
        return self.graph.subgraph(self.unscored_nodes_iter())


def multirun(graph, node, key, tag=None, default_score=None, runs=None):
    """Runs NPA multiple times and yields the NpaRunner object after each run has been completed

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param node: The BEL node that is the focus of this analysis
    :type node: tuple
    :param key: The key for the nodes' data dictionaries that points to their original experimental measurements
    :type key: str
    :param tag: The key for the nodes' data dictionaries where the NPA scores will be put. Defaults to 'score'
    :type tag: str
    :param default_score: The initial NPA score for all nodes. This number can go up or down.
    :type default_score: float
    :param runs: The number of times to run the NPA algorithm. Defaults to 1000.
    :type runs: int
    :return: An iterable over the runners after each iteration
    :rtype: iter
    """
    runs = 1000 if runs is None else runs

    for i in range(runs):
        try:
            runner = NpaRunner(graph, node, key, tag=tag, default_score=default_score)
            runner.run()
            yield runner
        except:
            log.debug('Run %s failed for %s', i, node)


def multirun_average(graph, node, key, tag=None, default_score=None, runs=None):
    """Gets the average NPA score over multiple runs.

    This function is very simple, and can be copied to do more interesting statistics over the :class:`NpaRunner`
    instances. To iterate over the runners themselves, see :func:`average_npa_run_helper`

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param node: The BEL node that is the focus of this analysis
    :type node: tuple
    :param key: The key for the nodes' data dictionaries that points to their original experimental measurements
    :type key: str
    :param tag: The key for the nodes' data dictionaries where the NPA scores will be put. Defaults to 'score'
    :type tag: str
    :param default_score: The initial NPA score for all nodes. This number can go up or down.
    :type default_score: float
    :param runs: The number of times to run the NPA algorithm. Defaults to 1000.
    :type runs: int
    :return: The average score for the target node
    :rtype: float
    """
    runners = multirun(graph, node, key, tag, default_score=default_score, runs=runs)
    scores = [runner.get_final_score() for runner in runners]

    if not scores:
        log.warning('Unable to run NPA on %s', node)
        return None

    return sum(scores) / len(scores)


def workflow(graph, node, key, tag=None, default_score=None, runs=None):
    """Generates candidate mechanism and runs NPA. retun

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param node: The BEL node that is the focus of this analysis
    :type node: tuple
    :param key: The key in the node data dictionary representing the experimental data
    :type key: str
    :param tag: The key for the nodes' data dictionaries where the NPA scores will be put. Defaults to 'score'
    :type tag: str
    :param default_score: The initial NPA score for all nodes. This number can go up or down.
    :type default_score: float
    :param runs: The number of times to run the NPA algorithm. Defaults to 1000.
    :type runs: int
    :return: A list of runners
    :rtype: list
    """
    sg = generate_mechanism(graph, node, key)
    runners = multirun(sg, node, key, tag=tag, default_score=default_score, runs=runs)
    return list(runners)


def workflow_all(graph, key, tag=None, default_score=None, runs=None):
    """Runs NPA and get runners for every possible candidate mechanism

    1. Get all biological processes
    2. Get candidate mechanism induced two level back from each biological process
    3. NPA on each candidate mechanism for multiple runs
    4. Return all runner results

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param key: The key in the node data dictionary representing the experimental data
    :type key: str
    :param tag: The key for the nodes' data dictionaries where the NPA scores will be put. Defaults to 'score'
    :type tag: str
    :param default_score: The initial NPA score for all nodes. This number can go up or down.
    :type default_score: float
    :param runs: The number of times to run the NPA algorithm. Defaults to 1000.
    :type runs: int
    :return: A dictionary of {node: list of runners}
    :rtype: dict
    """
    results = {}
    for node in get_nodes_by_function(graph, BIOPROCESS):
        results[node] = workflow(graph, node, key, tag=tag, default_score=default_score, runs=runs)
    return results


def workflow_all_average(graph, key, tag=None, default_score=None, runs=None):
    """Runs NPA to get average score for every possible candidate mechanism

    1. Get all biological processes
    2. Get candidate mechanism induced two level back from each biological process
    3. NPA on each candidate mechanism for multiple runs
    4. Report average NPA scores for each candidate mechanism

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param key: The key in the node data dictionary representing the experimental data
    :type key: str
    :param tag: The key for the nodes' data dictionaries where the NPA scores will be put. Defaults to 'score'
    :type tag: str
    :param default_score: The initial NPA score for all nodes. This number can go up or down.
    :type default_score: float
    :param runs: The number of times to run the NPA algorithm. Defaults to 1000.
    :type runs: int
    :return: A dictionary of {node: upstream causal subgraph}
    :rtype: dict
    """
    results = {}
    for node in get_nodes_by_function(graph, BIOPROCESS):
        sg = generate_mechanism(graph, node, key)
        try:
            results[node] = multirun_average(sg, node, key, tag=tag, default_score=default_score, runs=runs)
        except:
            log.exception('could not run on %', node)
    return results


# TODO implement
def calculate_average_npa_by_annotation(graph, key, annotation='Subgraph'):
    """For each subgraph induced over the edges matching the annotation, calculate the average NPA score
    for all of the contained biological processes

    Assumes you haven't done anything yet

    1. Calculates scores with pbt.analysis.npa.npa_all_bioprocesses
    2. Overlays data with pbt.integration.overlay_data
    3. Calculates averages with pbt.selection.group_nodes.average_node_annotation

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param key: The key in the node data dictionary representing the experimental data
    :type key: str
    :param annotation: A BEL annotation
    :type annotation: str
    """
    raise NotImplementedError
