# -*- coding: utf-8 -*-

__all__ = [
    'get_upstream_leaves',
    'get_unweighted_upstream_leaves'
]


def get_upstream_leaves(graph):
    """Gets all leaves of the graph (with no incoming edges and only one outgoing edge)

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    """
    for node, data in graph.nodes_iter(data=True):
        if 0 == len(graph.predecessors(node)) and 1 == len(graph.successors(node)):
            yield node


def get_unweighted_upstream_leaves(graph, key):
    """Gets all leaves of the graph with no incoming edges, one outgoing edge, and without the given key in
    its data dictionary

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param key: The key in the node data dictionary representing the experimental data
    :type key: str
    :return: An iterable over leaves (nodes with an in-degree of 0) that don't have the given annotation
    :rtype: iter
    """
    for node in get_upstream_leaves(graph):
        if key not in graph.node[node]:
            yield node
