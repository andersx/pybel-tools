# -*- coding: utf-8 -*-

"""

This module contains a set of default functions for filtering nodes and building node filtering functions

"""

from __future__ import print_function

from pybel.constants import FUNCTION, PATHOLOGY, OBJECT, SUBJECT, MODIFIER, ACTIVITY

__all__ = [
    'keep_node_permissive',
    'list_filter_builder',
    'function_filter_builder',
    'exclusion_filter_builder',
    'pathology_filter',
    'keep_molecularly_active',
    'concatenate_node_filters',
    'filter_nodes',
    'count_passed_node_filter',
    'summarize_node_filter',
]


# Example filter

def keep_node_permissive(graph, node):
    """A default node filter that is true for all nodes

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param node: The node
    :type node: tuple
    :return: True
    :rtype: bool
    """
    return True


# Filter Builders

def concatenate_node_filters(*filters):
    """Concatenates multiple node filters to a new filter that requires all filters to be met

    :param filters: a list of predicates (graph, node) -> bool
    :type filters: list
    :return: A combine filter (graph, node) -> bool
    :rtype: lambda
    """

    # If no filters are given, then return the trivially permissive filter
    if not filters:
        return keep_node_permissive

    # If only one filter is given, don't bother wrapping it
    if 1 == len(filters):
        return filters[0]

    def concatenated_filter(graph, node):
        return all(f(graph, node) for f in filters)

    return concatenated_filter


def list_filter_builder(nodes):
    """Builds a filter that fails on nodes in the given list

    :param nodes: An iterable of BEL nodes
    :type nodes: iter
    :return: A node filter (graph, node) -> bool
    :rtype: lambda
    """
    nodes = set(nodes)

    def list_filter(graph, node):
        return node in nodes

    return list_filter


def function_filter_builder(function):
    """Builds a filter that fails on nodes of the given function

    :param function: A BEL Function
    :type function: str
    :return: A node filter (graph, node) -> bool
    :rtype: lambda
    """

    def function_filter(graph, node):
        return graph.node[node][FUNCTION] != function

    return function_filter


def exclusion_filter_builder(*nodes):
    """Builds a filter that fails on nodes in the fiven list

    :param nodes: A list of nodes
    :type nodes: list
    :return: A node filter (graph, node) -> bool
    :rtype: lambda
    """

    def exclusion_filter(graph, node):
        return all(node != n for n in nodes)

    return exclusion_filter


# Default Filters

pathology_filter = function_filter_builder(PATHOLOGY)


def keep_molecularly_active(graph, node):
    """Returns true if the given node has a known molecular activity

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param node: A BEL node
    :type node: tuple
    :return: If the node has a known molecular activity
    :rtype: bool
    """
    for _, _, d in graph.in_edges(node):
        if OBJECT in d and MODIFIER in d[OBJECT] and d[OBJECT][MODIFIER] == ACTIVITY:
            return True

    for _, _, d in graph.out_edges(node):
        if SUBJECT in d and MODIFIER in d[SUBJECT] and d[SUBJECT][MODIFIER] == ACTIVITY:
            return True

    return False


# Appliers

def filter_nodes(graph, *filters):
    """Applies a set of filters to the nodes iterator of a BEL graph

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param filters: a list of filters
    :type filters: list
    :return: An iterable of nodes that pass all filters
    :rtype: iter
    """

    # If no filters are given, return the standard node iterator
    if not filters:
        for node in graph.nodes_iter():
            yield node
    else:
        concatenated_filter = concatenate_node_filters(*filters)
        for node in graph.nodes_iter():
            if concatenated_filter(graph, node):
                yield node


def count_passed_node_filter(graph, *filters):
    """Counts how many nodes pass a given set of filters

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param filters: a list of filters
    :type filters: list
    """
    return sum(1 for _ in filter_nodes(graph, *filters))


def summarize_node_filter(graph, *filters):
    """Prints a summary of the number of nodes passing a given set of filters

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param filters: a list of filters
    :type filters: list
    """
    passed = count_passed_node_filter(graph, *filters)
    print('{}/{} nodes passed {}'.format(passed, graph.number_of_nodes(), ', '.join(f.__name__ for f in filters)))
