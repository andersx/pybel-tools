# -*- coding: utf-8 -*-

from ..filters.node_filters import data_does_not_contain_key_builder, upstream_leaf_predicate

__all__ = [
    'get_upstream_leaves',
    'get_unweighted_upstream_leaves'
]


def get_upstream_leaves(graph):
    """Gets all leaves of the graph (with no incoming edges and only one outgoing edge)

    .. seealso:: :func:`upstream_leaf_predicate`

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :return: An iterator over nodes that are upstream leaves
    :rtype: iter
    """
    for node in graph.nodes_iter():
        if upstream_leaf_predicate(graph, node):
            yield node


def get_unweighted_upstream_leaves(graph, key):
    """Gets all leaves of the graph with no incoming edges, one outgoing edge, and without the given key in
    its data dictionary

    .. seealso :: :func:`data_does_not_contain_key_builder`

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param key: The key in the node data dictionary representing the experimental data
    :type key: str
    :return: An iterable over leaves (nodes with an in-degree of 0) that don't have the given annotation
    :rtype: iter
    """
    data_does_not_contain_key = data_does_not_contain_key_builder(key)

    for node in get_upstream_leaves(graph):
        if data_does_not_contain_key(graph, node):
            yield node
