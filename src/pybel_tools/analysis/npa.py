"""

An variant of the Network Pertubation Amplitude algorithm inspired by Reagon Kharki's implementation

"""

from __future__ import print_function

import logging

from pybel.canonicalize import calculate_canonical_name
from pybel.constants import RELATION, CAUSAL_DECREASE_RELATIONS, CAUSAL_INCREASE_RELATIONS, BIOPROCESS
from ..selection import get_nodes_by_function, get_upstream_causal_subgraph
from ..selection import get_upstream_leaves

__all__ = [
    'WEIGHT',
    'NPA_SCORE',
    'NPA_DEFAULT_SCORE',
    'NPA_HUB',
    'run_on_upstream_of_bioprocess',
    'run',
    'remove_unweighted_leaves',
]

log = logging.getLogger(__name__)

#: Signifies the NPA score in the node's data dictionary
NPA_SCORE = 'score'

#: The default score for NPA
NPA_DEFAULT_SCORE = 999.99

#: Signifies whether a node has predecessors in the node's data dictionary
NPA_HUB = 'hub'


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


def get_unweighted_leaves(graph, key):
    """

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param key: The key in the node data dictionary representing the experimental data
    :type key: str
    :return: An iterable over leaves (nodes with an in-degree of 0) that don't have the given annotation
    :rtype: iter
    """
    for node in get_upstream_leaves(graph):
        if key not in graph.node[node]:
            yield node


def remove_unweighted_leaves(graph, key):
    """

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param key: The key in the node data dictionary representing the experimental data
    :type key: str
    """
    unweighted_leaves = list(get_unweighted_leaves(graph, key))
    graph.remove_nodes_from(unweighted_leaves)


def remove_unweighted_sources(graph, key):
    """
    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param key: The key in the node data dictionary representing the experimental data
    :type key: str
    """
    for node in graph.nodes():
        if graph.in_degree(node) == 0 and key not in graph.node[node]:
            graph.remove_node(node)


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


def run(graph, key):
    """

    Nodes that don't have any predecessors can be calculated directly

    1. For nodes without predecessors, their differential gene expression score is assigned as their NPA score
    2. All nodes with predecessors

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param key: The key in the node data dictionary representing the experimental data
    :type key: str
    """
    for node in graph.nodes_iter():
        graph.node[node][NPA_SCORE] = NPA_DEFAULT_SCORE

        if not graph.predecessors(node):
            graph.node[node][NPA_SCORE] = graph.node[node].get(key, 0)
            graph.node[node][NPA_HUB] = False
        else:
            graph.node[node][NPA_HUB] = True

    all_hubs = {node for node in graph.nodes_iter() if graph.node[node][NPA_HUB]}

    hub_list = list(all_hubs)

    iteration_count = 0

    while hub_list:

        iteration_count += 1

        log.info('Iteration %s', iteration_count)

        remove = set()

        for node in hub_list:
            log.info('investigating node: %s', calculate_canonical_name(graph, node))

            if not any(predecessor in all_hubs for predecessor in graph.predecessors(node)):
                graph.node[node][NPA_SCORE] = calculate_npa_score_iteration(graph, node, key)
                remove.add(node)
                log.info('removing node: %s', calculate_canonical_name(graph, node))

        hub_list = [node for node in hub_list if node not in remove]
        log.info('remove list: %s', remove)

        if not remove:  # all previous hubs in the list have been considered
            get_score_central_hub(graph, all_hubs, hub_list, key)
            return


def get_score_central_hub(graph, all_hubs, hub_list, key):
    """Recursively scores central hubs

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param all_hubs: set
    :type hub_list: list
    :param key: The key in the node data dictionary representing the experimental data
    :type key: str

    """
    if not hub_list:
        return

    log.info('scoring hub list: %s', hub_list)
    new_hub_list = []

    for node in hub_list:
        if any(graph.node[predecessor][NPA_SCORE] == NPA_DEFAULT_SCORE for predecessor in
               graph.predecessors_iter(node)):
            new_hub_list.append(node)
        else:
            graph.node[node][NPA_SCORE] = calculate_npa_score_iteration(graph, node, key)

    get_score_central_hub(graph, all_hubs, new_hub_list, key)


def calculate_npa_score_iteration(graph, node, key):
    """Calculates the score of the given node

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param node: A node in the BEL graph
    :type node: tuple
    :param key: The key in the node data dictionary representing the experimental data
    :type key: str
    :return: The new weight of the node
    :rtype: float
    """

    if key not in graph.node[node]:
        print(node)

    score = graph.node[node][key]

    for predecessor, _, d in graph.in_edges_iter(node, data=True):
        if RELATION not in d:
            print(predecessor, node, d)

        if d[RELATION] in CAUSAL_INCREASE_RELATIONS:
            score += graph.node[predecessor][NPA_SCORE]
        elif d[RELATION] in CAUSAL_DECREASE_RELATIONS:
            score -= graph.node[predecessor][NPA_SCORE]

    return score
