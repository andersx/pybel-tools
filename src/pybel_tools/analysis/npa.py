"""

An variant of the Network Pertubation Amplitude algorithm inspired by Reagon Kharki's implementation

"""

from __future__ import print_function

import logging

from pybel.canonicalize import calculate_canonical_name
from pybel.constants import RELATION, CAUSAL_DECREASE_RELATIONS, CAUSAL_INCREASE_RELATIONS, BIOPROCESS
from ..selection import get_nodes_by_function, get_upstream_causal_subgraph

__all__ = [
    'WEIGHT',
    'SCORE',
    'DEFAULT_SCORE',
    'HUB',
    'run_on_upstream_of_bioprocess',
    'run',
    'prune_unweighted_leaves',
]

log = logging.getLogger(__name__)

#: Signifies the initial gene expression/NPA score
WEIGHT = 'weight'

#: Signifies the NPA score in the node's data dictionary
SCORE = 'score'

#: The default score for NPA
DEFAULT_SCORE = 999.99

#: Signifies whether a node has predecessors in the node's data dictionary
HUB = 'hub'


# TODO implement
def calculate_average_npa_by_annotation(graph, annotation='Subgraph', weight=WEIGHT):
    """For each subgraph induced over the edges matching the annotation, calculate the average NPA score
    for all of the contained biological processes

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param annotation: A BEL annotation
    :type annotation: str
    :param weight: The key in the node data dictionary representing the experimental data
    :type weight: str
    """
    raise NotImplementedError


def _get_unweighted_leaves(graph, weight):
    """

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param weight: The key in the node data dictionary representing the experimental data
    :type weight: str
    :return: An iterable over leaves (nodes with an in-degree of 0) that don't have the given annotation
    :rtype: iter
    """
    for node in graph.nodes_iter():
        if graph.in_degree(node) == 0 and graph.out_degree(node) == 1 and weight not in graph.node[node]:
            yield node


def prune_unweighted_leaves(graph, weight):
    """

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param weight: The key in the node data dictionary representing the experimental data
    :type weight: str
    """
    unweighted_leaves = list(_get_unweighted_leaves(graph, weight))
    graph.remove_nodes_from(unweighted_leaves)


def run_on_upstream_of_bioprocess(graph, weight):
    """Runs NPA on graphs constrained to be strictly one element upstream of biological processes.
    This function can be later extended to go back multiple levels.

    1. Get all biological processes
    2. Get subgraphs induced one level back from each biological process
    3. NPA on each induced subgraph

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param weight: The key in the node data dictionary representing the experimental data
    :type weight: str
    :return: A dictionary of {node: upstream causal subgraph}
    :rtype: dict
    """

    nodes = list(get_nodes_by_function(graph, BIOPROCESS))

    sgs = {node: get_upstream_causal_subgraph(graph, node) for node in nodes}

    for sg in sgs.values():
        run(sg, weight=weight)

    return sgs


def run(graph, weight):
    """

    Nodes that don't have any predecessors can be calculated directly

    1. For nodes without predecessors, their differential gene expression score is assigned as their NPA score
    2. All nodes with predecessors

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param weight: The key in the node data dictionary representing the experimental data
    :type weight: str
    """
    for node in graph.nodes_iter():
        graph.node[node][SCORE] = DEFAULT_SCORE

        if not graph.predecessors(node):
            graph.node[node][SCORE] = graph.node[node].get(weight, 0)
            graph.node[node][HUB] = False
        else:
            graph.node[node][HUB] = True

    all_hubs = {node for node in graph.nodes_iter() if graph.node[node][HUB]}

    hub_list = list(all_hubs)

    iteration_count = 0

    while hub_list:

        iteration_count += 1

        log.info('Iteration %s', iteration_count)

        remove = set()

        for node in hub_list:
            log.info('investigating node: %s', calculate_canonical_name(graph, node))

            if not any(predecessor in all_hubs for predecessor in graph.predecessors(node)):
                graph.node[node][SCORE] = calculate_npa_score_iteration(graph, node, weight)
                remove.add(node)
                log.info('removing node: %s', calculate_canonical_name(graph, node))

        hub_list = [node for node in hub_list if node not in remove]
        log.info('remove list: %s', remove)

        if not remove:  # all previous hubs in the list have been considered
            get_score_central_hub(graph, all_hubs, hub_list, weight)
            return


def get_score_central_hub(graph, all_hubs, hub_list, weight):
    """Recursively scores central hubs

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param all_hubs: set
    :type hub_list: list
    :param weight: The label for the NPA node weight

    """
    if not hub_list:
        return

    log.info('scoring hub list: %s', hub_list)
    new_hub_list = []

    for node in hub_list:
        if any(graph.node[predecessor][SCORE] == DEFAULT_SCORE for predecessor in graph.predecessors_iter(node)):
            new_hub_list.append(node)
        else:
            graph.node[node][SCORE] = calculate_npa_score_iteration(graph, node, weight)

    get_score_central_hub(graph, all_hubs, new_hub_list, weight)


def calculate_npa_score_iteration(graph, node, weight):
    """Calculates the score of the given node

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param node: A node in the BEL graph
    :type node: tuple
    :param weight: The tag for the weight
    :type weight: str
    :return: The new weight of the node
    :rtype: float
    """

    score = graph.node[node][weight]

    for predecessor in graph.predecessors_iter(node):
        if graph.edge[predecessor][node][RELATION] in CAUSAL_INCREASE_RELATIONS:
            score += graph.node[predecessor][SCORE]
        elif graph.edge[predecessor][node][RELATION] in CAUSAL_DECREASE_RELATIONS:
            score -= graph.node[predecessor][SCORE]

    return score
