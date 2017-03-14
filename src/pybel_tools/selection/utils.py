# -*- coding: utf-8 -*-

from itertools import combinations

from pybel.constants import FUNCTION

__all__ = [
    'get_nodes_by_function',
    'get_triangles',
]


def get_nodes_by_function(graph, function):
    """Get all nodes of a given type

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param function: The BEL function to filter by
    :type function: str
    :return: An iterable of all BEL nodes with the given function
    :rtype: iter
    """
    for node, data in graph.nodes_iter(data=True):
        if data[FUNCTION] == function:
            yield node


def get_triangles(graph, node):
    """Yields all triangles pointed by the given node

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param node: The source node
    :type node: tuple
    """
    for a, b in combinations(graph.edge[node], 2):
        if graph.edge[a][b]:
            yield a, b
        if graph.edge[b][a]:
            yield b, a
