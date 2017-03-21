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

from pybel.constants import RELATION, CAUSAL_RELATIONS, ANNOTATIONS
from ..utils import check_has_annotation

__all__ = [
    'keep_edge_permissive',
    'keep_causal_edges',
    'concatenate_edge_filters',
    'filter_edges',
    'count_passed_edge_filter',
    'summarize_edge_filter'
]


def keep_edge_permissive(graph, u, v, k, d):
    """Passes for all edges

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param u: A BEL node
    :type u: tuple
    :param v: A BEL node
    :type v: tuple
    :param k: The edge key between the given nodes
    :type k: int
    :param d: The edge data dictionary
    :type d: dict
    :return: Always returns :code:`True`
    :rtype: bool
    """
    return True


def keep_causal_edges(graph, u, v, k, d):
    """Only passes on causal edges, belonging to the set :data:`pybel.constants.CAUSAL_RELATIONS`

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param u: A BEL node
    :type u: tuple
    :param v: A BEL node
    :type v: tuple
    :param k: The edge key between the given nodes
    :type k: int
    :param d: The edge data dictionary
    :type d: dict
    :return: True if the edge is a causal edge
    :rtype: bool
    """
    return graph.edge[u][v][k][RELATION] in CAUSAL_RELATIONS


def build_annotation_value_filter(annotation, value):
    def annotation_value_filter(graph, u, v, k, attr_dict):
        if not check_has_annotation(graph.edge[u][v][k], annotation):
            return False
        return graph.edge[u][v][k][ANNOTATIONS][annotation] == value

    return annotation_value_filter


def build_relation_filter(relations):
    if isinstance(relations, str):
        def relation_filter(graph, u, v, k, attr_dict):
            return graph.edge[u][v][k][RELATION] == relations

        return relation_filter
    elif isinstance(relations, (list, tuple, set)):
        def relation_filter(graph, u, v, k, attr_dict):
            return graph.edge[u][v][k][RELATION] in relations

        return relation_filter
    else:
        raise ValueError('Invalid type for argument: {}'.format(relations))


def concatenate_edge_filters(filters):
    """Concatenates multiple edge filters to a new filter that requires all filters to be met.

    :param filters: a list of predicates (graph, node, node, key, data) -> bool
    :type filters: list or tuple or lambda
    :return: A combine filter (graph, node, node, key, data) -> bool
    :rtype: lambda
    """

    # If no filters are given, then return the trivially permissive filter
    if not filters:
        return keep_edge_permissive

    # If a filter outside a list is given, just return it
    if not isinstance(filters, (list, tuple)):
        return filters

    # If only one filter is given, don't bother wrapping it
    if 1 == len(filters):
        return filters[0]

    def concatenated_edge_filter(graph, u, v, k, d):
        """Passes only for an edge that pass all enclosed filters

        :param graph: A BEL Graph
        :type graph: pybel.BELGraph
        :param u: A BEL node
        :type u: tuple
        :param v: A BEL node
        :type v: tuple
        :param k: The edge key between the given nodes
        :type k: int
        :param d: The edge data dictionary
        :type d: dict
        :return: If the edge passes all enclosed filters
        :rtype: bool
        """
        return all(f(graph, u, v, k, d) for f in filters)

    return concatenated_edge_filter


def filter_edges(graph, filters):
    """Applies a set of filters to the edges iterator of a BEL graph

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param filters: A filter or list of filters
    :type filters: list or tuple or lambda
    :return: An iterable of edges that pass all filters
    :rtype: iter
    """

    # If no filters are given, return the standard edge iterator
    if not filters:
        for u, v, k, d in graph.edges_iter(keys=True, data=True):
            yield u, v, k, d
    else:
        concatenated_edge_filter = concatenate_edge_filters(filters)
        for u, v, k, d in graph.edges_iter(keys=True, data=True):
            if concatenated_edge_filter(graph, u, v, k, d):
                yield u, v, k, d


def count_passed_edge_filter(graph, filters):
    """Returns the number of edges passing a given set of filters

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param filters: A filter or list of filters
    :type filters: list or tuple or lambda
    :return: The number of edges passing a given set of filters
    :rtype: int
    """
    return sum(1 for _ in filter_edges(graph, filters))


def summarize_edge_filter(graph, filters):
    """Prints a summary of the number of edges passing a given set of filters

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param filters: A filter or list of filters
    :type filters: list or tuple or lamba
    """
    passed = count_passed_edge_filter(graph, filters)
    print('{}/{} edges passed {}'.format(passed, graph.number_of_edges(), ', '.join(f.__name__ for f in filters)))
