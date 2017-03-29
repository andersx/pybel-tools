# -*- coding: utf-8 -*-

"""
Node Filters
------------

A node filter is a function that takes two arguments: a :class:`pybel.BELGraph` and a node tuple. It returns a boolean
representing whether the node passed the given test.

This module contains a set of default functions for filtering lists of nodes and building node filtering functions.

A general use for a node filter function is to use the built-in :func:`filter` in code like
:code:`filter(your_node_filter, graph.nodes_iter())`
"""

from __future__ import print_function

from pybel.constants import FUNCTION, PATHOLOGY, OBJECT, SUBJECT, MODIFIER, ACTIVITY

__all__ = [
    'keep_node_permissive',
    'node_inclusion_filter_builder',
    'node_exclusion_filter_builder',
    'function_inclusion_filter_builder',
    'function_exclusion_filter_builder',
    'include_pathology_filter',
    'exclude_pathology_filter',
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
    :return: Always returns :code:`True`
    :rtype: bool
    """
    return True


def node_inclusion_filter_builder(nodes):
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


def node_exclusion_filter_builder(nodes):
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


def function_inclusion_filter_builder(function):
    """Builds a filter that only passes on nodes of the given function(s)

    :param function: A BEL Function or list/set/tuple of BEL functions
    :type function: str or list or tuple or set
    :return: A node filter (graph, node) -> bool
    :rtype: lambda
    """

    if isinstance(function, str):
        def function_inclusion_filter(graph, node):
            """Passes only for a node that has the enclosed function

            :param graph: A BEL Graph
            :type graph: pybel.BELGraph
            :param node: A BEL node
            :type node: tuple
            :return: If the node doesn't have the enclosed function
            :rtype: bool
            """
            return graph.node[node][FUNCTION] == function

        return function_inclusion_filter

    elif isinstance(function, (list, tuple, set)):
        functions = set(function)

        def functions_inclusion_filter(graph, node):
            """Passes only for a node that is one of the enclosed functions

            :param graph: A BEL Graph
            :type graph: pybel.BELGraph
            :param node: A BEL node
            :type node: tuple
            :return: If the node doesn't have the enclosed functions
            :rtype: bool
            """
            return graph.node[node][FUNCTION] in functions

        return functions_inclusion_filter

    raise ValueError('Invalid type for argument: {}'.format(function))


def function_exclusion_filter_builder(function):
    """Builds a filter that fails on nodes of the given function(s)

    :param function: A BEL Function or list/set/tuple of BEL functions
    :type function: str or list or tuple or set
    :return: A node filter (graph, node) -> bool
    :rtype: lambda
    """

    if isinstance(function, str):
        def function_exclusion_filter(graph, node):
            """Passes only for a node that doesn't have the enclosed function

            :param graph: A BEL Graph
            :type graph: pybel.BELGraph
            :param node: A BEL node
            :type node: tuple
            :return: If the node doesn't have the enclosed function
            :rtype: bool
            """
            return graph.node[node][FUNCTION] != function

        return function_exclusion_filter

    elif isinstance(function, (list, tuple, set)):
        functions = set(function)

        def functions_exclusion_filter(graph, node):
            """Passes only for a node that doesn't have the enclosed functions

            :param graph: A BEL Graph
            :type graph: pybel.BELGraph
            :param node: A BEL node
            :type node: tuple
            :return: If the node doesn't have the enclosed functions
            :rtype: bool
            """
            return graph.node[node][FUNCTION] not in functions

        return functions_exclusion_filter

    raise ValueError('Invalid type for argument: {}'.format(function))


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

def concatenate_node_filters(filters):
    """Concatenates multiple node filters to a new filter that requires all filters to be met

    :param filters: a list of predicates (graph, node) -> bool
    :type filters: list
    :return: A combine filter (graph, node) -> bool
    :rtype: lambda

    Example usage:

    >>> from pybel.constants import GENE, PROTEIN, PATHOLOGY
    >>> path_filter = function_exclusion_filter_builder(PATHOLOGY)
    >>> app_filter = node_exclusion_filter_builder([(PROTEIN, 'HGNC', 'APP'), (GENE, 'HGNC', 'APP')])
    >>> my_filter = concatenate_node_filters([path_filter, app_filter])
    """

    # If no filters are given, then return the trivially permissive filter
    if not filters:
        return keep_node_permissive

    # If a filter outside a list is given, just return it
    if not isinstance(filters, (list, tuple)):
        return filters

    # If only one filter is given, don't bother wrapping it
    if 1 == len(filters):
        return filters[0]

    def concatenated_node_filter(graph, node):
        """Passes only for a nodes that pass all enclosed filters

        :param graph: A BEL Graph
        :type graph: pybel.BELGraph
        :param node: A BEL node
        :type node: tuple
        :return: If the node passes all enclosed filters
        :rtype: bool
        """
        return all(f(graph, node) for f in filters)

    return concatenated_node_filter


# Default Filters

#: A filter that passes for nodes that are :data:`pybel.constants.PATHOLOGY`
include_pathology_filter = function_inclusion_filter_builder(PATHOLOGY)

#: A filter that fails for nodes that are :data:`pybel.constants.PATHOLOGY`
exclude_pathology_filter = function_exclusion_filter_builder(PATHOLOGY)


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

def filter_nodes(graph, filters):
    """Applies a set of filters to the nodes iterator of a BEL graph

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param filters: A node filter or list/tuple of node filters
    :type filters: list or tuple or lambda
    :return: An iterable of nodes that pass all filters
    :rtype: iter
    """

    # If no filters are given, return the standard node iterator
    if not filters:
        for node in graph.nodes_iter():
            yield node
    else:
        concatenated_filter = concatenate_node_filters(filters)
        for node in graph.nodes_iter():
            if concatenated_filter(graph, node):
                yield node


def count_passed_node_filter(graph, filters):
    """Counts how many nodes pass a given set of filters

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param filters: A node filter or list/tuple of node filters
    :type filters: list
    """
    return sum(1 for _ in filter_nodes(graph, filters))


def summarize_node_filter(graph, filters):
    """Prints a summary of the number of nodes passing a given set of filters

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param filters: A node filter or list/tuple of node filters
    :type filters: list or tuple or lambda
    """
    passed = count_passed_node_filter(graph, filters)
    print('{}/{} nodes passed {}'.format(passed, graph.number_of_nodes(), ', '.join(f.__name__ for f in filters)))
