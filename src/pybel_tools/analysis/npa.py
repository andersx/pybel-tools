"""

An variant of the Network Pertubation Amplitude algorithm inspired by Reagon Kharki's implementation

@auth

"""

from __future__ import print_function

import logging

from pybel.canonicalize import calculate_canonical_name
from pybel.constants import RELATION, CAUSAL_DECREASE_RELATIONS, CAUSAL_INCREASE_RELATIONS

log = logging.getLogger(__name__)

#: Signifies the initial gene expression/NPA score
WEIGHT = 'weight'

#: Signifies the NPA score in the node's data dictionary
SCORE = 'score'

#: The default score for NPA
DEFAULT_SCORE = 999.99

#: Signifies whether a node has predecessors in the node's data dictionary
HUB = 'hub'


def run(graph, weight=WEIGHT):
    """

    Nodes that don't have any predecessors can be calculated directly

    1. For nodes without predecessors, their differential gene expression score is assigned as their NPA score
    2. All nodes with predecessors

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param weight: The key in the node data dictionary representing the experimental data
    :type weight: str
    :return:
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
                graph.node[node][SCORE] = calculate_npa_score_iteration(graph, node)
                remove.add(node)
                log.info('removing node: %s', calculate_canonical_name(graph, node))

        hub_list = [node for node in hub_list if node not in remove]
        log.info('remove list: %s', remove)

        if not remove:  # all previous hubs in the list have been considered
            get_score_central_hub(graph, all_hubs, hub_list)
            return


def get_score_central_hub(graph, all_hubs, hub_list):
    """Recursively scores central hubs

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param all_hubs: set
    :type hub_list: list

    """
    if not hub_list:
        return

    log.info('scoring hub list: %s', hub_list)
    new_hub_list = []

    for node in hub_list:
        if any(graph.node[predecessor][SCORE] == DEFAULT_SCORE for predecessor in graph.predecessors_iter(node)):
            new_hub_list.append(node)
        else:
            graph.node[node][SCORE] = calculate_npa_score_iteration(graph, node)

    get_score_central_hub(graph, all_hubs, new_hub_list)


def calculate_npa_score_iteration(graph, node):
    """Calculates the score of the given node

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param node: A node in the BEL graph
    :type node: tuple
    :return: The new weight of the node
    :rtype: float
    """

    score = graph.node[node][WEIGHT]

    for predecessor in graph.predecessors_iter(node):
        if graph.edge[predecessor][node][RELATION] in CAUSAL_INCREASE_RELATIONS:
            score += graph.node[predecessor][SCORE]
        elif graph.edge[predecessor][node][RELATION] in CAUSAL_DECREASE_RELATIONS:
            score -= graph.node[predecessor][SCORE]

    return score
