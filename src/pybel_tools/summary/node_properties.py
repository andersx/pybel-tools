# -*- coding: utf-8 -*-

"""This module contains functions that calculate properties of nodes"""

from collections import Counter

import networkx as nx

from pybel.constants import *
from ..filters.node_filters import get_nodes, node_has_molecular_activity, node_is_degraded, node_is_translocated

__all__ = [
    'is_causal_relation',
    'get_causal_out_edges',
    'get_causal_in_edges',
    'has_causal_out_edges',
    'has_causal_in_edges',
    'is_causal_source',
    'is_causal_central',
    'is_causal_sink',
    'get_causal_source_nodes',
    'get_causal_central_nodes',
    'get_causal_sink_nodes',
    'get_degradations',
    'get_activities',
    'get_translocated',
]


def is_causal_relation(graph, u, v, d):
    return d[RELATION] in CAUSAL_RELATIONS


def get_causal_out_edges(graph, node):
    """Gets the out-edges to the given node that are causal

    :param pybel.BELGraph graph: A BEL graph
    :param node: A node
    :type node: tuple
    :return: A set of (source, target) pairs where the source is the given node
    :rtype: set
    """
    return {
        (u, v)
        for u, v, d in graph.out_edges_iter(node, data=True)
        if is_causal_relation(graph, u, v, d)
    }


def get_causal_in_edges(graph, node):
    """Gets the in-edges to the given node that are causal

    :param pybel.BELGraph graph: A BEL graph
    :param node: A node
    :type node: tuple
    :return: A set of (source, target) pairs where the target is the given node
    :rtype: set
    """
    return {
        (u, v)
        for u, v, d in graph.in_edges_iter(node, data=True)
        if is_causal_relation(graph, u, v, d)
    }


def has_causal_out_edges(graph, node):
    """Gets if the node has causal out edges

    :param pybel.BELGraph graph: A BEL graph
    :param node: A node
    :type node: tuple
    :return: If the node has causal out edges
    :rtype: bool
    """
    return any(
        d[RELATION] in CAUSAL_RELATIONS
        for u, v, d in graph.out_edges_iter(node, data=True)
    )


def has_causal_in_edges(graph, node):
    """Gets if the node has causal in edges

    :param pybel.BELGraph graph: A BEL graph
    :param node: A node
    :type node: tuple
    :return: If the node has causal in edges
    :rtype: bool
    """
    return any(
        d[RELATION] in CAUSAL_RELATIONS
        for _, _, d in graph.in_edges_iter(node, data=True)
    )


def is_causal_source(graph, node):
    return not has_causal_in_edges(graph, node) and has_causal_out_edges(graph, node)


def is_causal_central(graph, node):
    return has_causal_in_edges(graph, node) and has_causal_out_edges(graph, node)


def is_causal_sink(graph, node):
    return has_causal_in_edges(graph, node) and not has_causal_out_edges(graph, node)


def get_causal_source_nodes(graph, function):
    """Returns a set of all nodes that have an in-degree of 0, which likely means that it is an external
    perterbagen and is not known to have any causal origin from within the biological system.

    These nodes are useful to identify because they generally don't provide any mechanistic insight.

    :param pybel.BELGraph graph: A BEL graph
    :param function: The function to filter by
    :type function: str
    :return: A set of source nodes
    :rtype: set
    """
    return {
        node
        for node, data in graph.nodes_iter(data=True)
        if data[FUNCTION] == function and is_causal_source(graph, node)
    }


def get_causal_central_nodes(graph, function):
    """Returns a set of all nodes that have both an in-degree > 0 and out-degree > 0. This means
    that they are an integral part of a pathway, since they are both produced and consumed.

    :param pybel.BELGraph graph: A BEL graph
    :param function: The function to filter by
    :type function: str
    :return: A set of central ABUNDANCE nodes
    :rtype: set
    """
    return {
        node
        for node, data in graph.nodes_iter(data=True)
        if data[FUNCTION] == function and is_causal_central(graph, node)
    }


def get_causal_sink_nodes(graph, function):
    """Returns a set of all ABUNDANCE nodes that have an causal out-degree of 0, which likely means that the knowledge
    assembly is incomplete, or there is a curation error.

    :param pybel.BELGraph graph: A BEL graph
    :param function: The function to filter by
    :type function: str
    :return: A set of sink ABUNDANCE nodes
    :rtype: set
    """
    return {
        node
        for node, data in graph.nodes_iter(data=True)
        if data[FUNCTION] == function and is_causal_sink(graph, node)
    }


def get_degradations(graph):
    """Gets all nodes that are degraded

    :param pybel.BELGraph graph: A BEL graph
    :return: A set of nodes that are degraded
    :rtype: set
    """
    return get_nodes(graph, node_is_degraded)


def get_activities(graph):
    """Gets all nodes that have molecular activities

    :param pybel.BELGraph graph: A BEL graph
    :return: A set of nodes that have molecular activities
    :rtype: set
    """
    return get_nodes(graph, node_has_molecular_activity)


def get_translocated(graph):
    """Gets all nodes that are translocated

    :param pybel.BELGraph graph: A BEL graph
    :return: A set of nodes that are translocated
    :rtype: set
    """
    return get_nodes(graph, node_is_translocated)


def node_has_variant(graph, node):
    return VARIANTS in graph.node[node]


def count_variants(graph):
    """Counts how many of each type of variant a graph has"""
    return Counter(
        variant_data[KIND]
        for node, data in graph.nodes_iter(data=True)
        if node_has_variant(graph, node)
        for variant_data in data[VARIANTS]
    )


def count_top_degrees(graph, number=30):
    dd = graph.degree()
    dc = Counter(dd)
    return dict(dc.most_common(number))


def count_top_centrality(graph, number=30):
    dd = nx.betweenness_centrality(graph)
    dc = Counter(dd)
    return dict(dc.most_common(number))
