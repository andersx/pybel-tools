# -*- coding: utf-8 -*-

"""
Edge Filters
------------

A edge filter is a function that takes five arguments: a :class:`pybel.BELGraph`, a source node tuple, a target node
tuple, a key, and a data dictionary. It returns a boolean representing whether the edge passed the given test.

This module contains a set of default functions for filtering lists of edges and building edge filtering functions.

A general use for an edge filter function is to use the built-in :func:`filter` in code like
:code:`filter(your_edge_filter, graph.edges_iter(keys=True, data=True))`
"""

from pybel.constants import RELATION, CAUSAL_RELATIONS

__all__ = [
    'keep_edge_permissive',
    'keep_causal_edges',
    'concatenate_edge_filters',
    'filter_edges',
    'count_passed_edge_filter',
    'summarize_edge_filter'
]


def keep_edge_permissive(graph, u, v, k, d):
    return True


def keep_causal_edges(graph, u, v, k, d):
    return d[RELATION] in CAUSAL_RELATIONS


def concatenate_edge_filters(*filters):
    """Concatenates multiple edge filters to a new filter that requires all filters to be met

    :param filters: a list of predicates (graph, node, node, key, data) -> bool
    :type filters: list
    :return: A combine filter (graph, node, node, key, data) -> bool
    :rtype: lambda
    """

    # If no filters are given, then return the trivially permissive filter
    if not filters:
        return keep_edge_permissive

    # If only one filter is given, don't bother wrapping it
    if 1 == len(filters):
        return filters[0]

    def concatenated_filter(graph, u, v, k, d):
        return all(f(graph, u, v, k, d) for f in filters)

    return concatenated_filter


def filter_edges(graph, *filters):
    """Applies a set of filters to the edges iterator of a BEL graph

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param filters: a list of filters
    :type filters: list
    :return: An iterable of edges that pass all filters
    :rtype: iter
    """

    # If no filters are given, return the standard node iterator
    if not filters:
        for edge in graph.edges_iter(keys=True, data=True):
            yield edge
    else:
        concatenated_filter = concatenate_edge_filters(*filters)
        for u, v, k, d in graph.edges_iter():
            if concatenated_filter(graph, u, v, k, d):
                yield u, v, k, d


def count_passed_edge_filter(graph, *filters):
    """Returns the number of edges passing a given set of filters

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param filters: a list of filters
    :type filters: list
    :return: The number of edges passing a given set of filters
    :rtype: int
    """
    return sum(1 for _ in filter_edges(graph, *filters))


def summarize_edge_filter(graph, *filters):
    """Prints a summary of the number of edges passing a given set of filters

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param filters: a list of filters
    :type filters: list
    """
    passed = count_passed_edge_filter(graph, *filters)
    print('{}/{} edges passed {}'.format(passed, graph.number_of_edges(), ', '.join(f.__name__ for f in filters)))
