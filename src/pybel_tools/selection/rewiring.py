# -*- coding: utf-8 -*-

"""

This module has functions that help produce random permutations over networks.

Random permutations are useful in statistical testing over aggregate statistics.

"""

import random

from ..utils import is_edge_consistent


def all_edges_consistent(graph):
    """Returns if all edges are consistent in a graph. Wraps :func:`pybel_tools.utils.is_edge_consistent`

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :return: Are all edges consistent
    :rtype: bool
    """
    return all(is_edge_consistent(graph, u, v) for u, v in graph.edges_iter())


def rewire_targets(graph, p):
    """Rewires a graph's edges' target nodes


    - For BEL graphs, assumes edge consistency (all edges between two given nodes are have the same relation)
    - Doesn't make self-edges

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param p: The probability of rewiring
    :return: A rewired BEL graph
    """

    if not all_edges_consistent(graph):
        raise ValueError('{} is not consistent'.format(graph))

    bg = graph.copy()
    nodes = bg.nodes()

    for u, v in bg.edges():
        if random.random() < p:
            continue

        w = random.choice(nodes)

        while w == u or bg.has_edge(u, w):
            w = random.choice(nodes)

        bg.add_edge(w, v)
        bg.remove_edge(u, v)

    return bg
