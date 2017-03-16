# -*- coding: utf-8 -*-

"""

This module contains a set of default functions for filtering nodes and building node filtering functions

The signature of the built-in method, :func:`filter`, is (function, iterable)

All node filters should be applicable if the iterable is graph.nodes_iter() such that

filter(your_node_filter, graph.nodes_iter()) is applicable.

"""

from __future__ import print_function

from pybel.constants import FUNCTION, PATHOLOGY, OBJECT, SUBJECT, MODIFIER, ACTIVITY

__all__ = [
    'keep_node_permissive',
    'inclusion_filter_builder',
    'function_exclusion_filter_builder',
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
    """A default node filter that always evaluates to :code:`True`.

    Given BEL graph :code:`graph`, applying :func:`keep_node_permissive` with a filter on the nodes iterable
    as in :code:`filter(keep_node_permissive, graph.nodes_iter())` will result in the same iterable as
    :code:`graph.nodes_iter()`

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param node: The node
    :type node: tuple
    :return: True
    :rtype: bool
    """
    return True


def inclusion_filter_builder(nodes):
    """Builds a filter that only passes on nodes in the given list

    :param nodes: A list of BEL nodes
    :type nodes: list
    :return: A node filter (graph, node) -> bool
    :rtype: lambda
    """
    node_set = set(nodes)

    def inclusion_filter(graph, node):
        """Passes only for a node that is in the enclosed node list

        :param graph: A BEL Graph
        :type graph: pybel.BELGraph
        :param node: A BEL node
        :type node: tuple
        :return: If the node is contained within the enclosed node list
        :rtype: bool
        """
        return node in node_set

    return inclusion_filter


def exclusion_filter_builder(nodes):
    """Builds a filter that fails on nodes in the given list

    :param nodes: A list of nodes
    :type nodes: list
    :return: A node filter (graph, node) -> bool
    :rtype: lambda
    """
    node_set = set(nodes)

    def exclusion_filter(graph, node):
        """Passes only for a node that isn't in the enclosed node list

        :param graph: A BEL Graph
        :type graph: pybel.BELGraph
        :param node: A BEL node
        :type node: tuple
        :return: If the node isn't contained within the enclosed node list
        :rtype: bool
        """
        return node not in node_set

    return exclusion_filter


def function_exclusion_filter_builder(function):
    """Builds a filter that fails on nodes of the given function

    :param function: A BEL Function
    :type function: str
    :return: A node filter (graph, node) -> bool
    :rtype: lambda
    """

    def function_exclusion_filter(graph, node):
        """Passes only for a node that doesn't have the enclosed function

        :param graph: A BEL Graph
        :type graph: pybel.BELGraph
        :param node: A BEL node
        :type node: tuple
        :return: If the node doesn't have the enclosed function
        :rtype: bool
        """
        return function != graph.node[node][FUNCTION]

    return function_exclusion_filter


def data_does_not_contain_key_builder(key):
    """Builds a filter that passes only on nodes that don't have the given key in their data dictionary

    :param key: A key for the node's data dictionary
    :type key: str
    :return: A node filter (graph, node) -> bool
    :rtype: lambda
    """

    def data_does_not_contain_key(graph, node):
        """Passes only for a node that doesn't contain the enclosed key in its data dictionary

        :param graph: A BEL Graph
        :type graph: pybel.BELGraph
        :param node: A BEL node
        :type node: tuple
        :return: If the node doesn't contain the enclosed key in its data dictionary
        :rtype: bool
        """
        return key not in graph.node[node]

    return data_does_not_contain_key


# Filter Builders

def concatenate_node_filters(*filters):
    """Concatenates multiple node filters to a new filter that requires all filters to be met

    :param filters: a list of predicates (graph, node) -> bool
    :type filters: list
    :return: A combine filter (graph, node) -> bool
    :rtype: lambda

    Example usage:

    >>> from pybel.constants import GENE, PROTEIN, PATHOLOGY
    >>> path_filter = function_exclusion_filter_builder(PATHOLOGY)
    >>> app_filter = exclusion_filter_builder([(PROTEIN, 'HGNC', 'APP'), (GENE, 'HGNC', 'APP')])
    >>> my_filter = concatenate_node_filters(path_filter, app_filter)
    """

    # If no filters are given, then return the trivially permissive filter
    if not filters:
        return keep_node_permissive

    # If only one filter is given, don't bother wrapping it
    if 1 == len(filters):
        return filters[0]

    def concatenated_filter(graph, node):
        """Passes only for a nodes that pass all enclosed filters

        :param graph: A BEL Graph
        :type graph: pybel.BELGraph
        :param node: A BEL node
        :type node: tuple
        :return: If the node passes all enclosed filters
        :rtype: bool
        """
        return all(f(graph, node) for f in filters)

    return concatenated_filter


# Default Filters

pathology_filter = function_exclusion_filter_builder(PATHOLOGY)


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


def upstream_leaf_predicate(graph, node):
    """Returns if the node is an upstream leaf. An upstream leaf is defined as a node that has no in-edges, and exactly
    1 out-edge.

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param node: A BEL node
    :type node: tuple
    :return: If the node is an upstream leaf
    :rtype: bool
    """
    return 0 == len(graph.predecessors(node)) and 1 == len(graph.successors(node))


# TODO node filter that is false for abundances with no in-edges

# Appliers

def filter_nodes(graph, *filters):
    """Applies a set of filters to the nodes iterator of a BEL graph

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param filters: A list of filters
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
    :param filters: A list of filters
    :type filters: list
    """
    return sum(1 for _ in filter_nodes(graph, *filters))


def summarize_node_filter(graph, *filters):
    """Prints a summary of the number of nodes passing a given set of filters

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param filters: A list of filters
    :type filters: list
    """
    passed = count_passed_node_filter(graph, *filters)
    print('{}/{} nodes passed {}'.format(passed, graph.number_of_nodes(), ', '.join(f.__name__ for f in filters)))
