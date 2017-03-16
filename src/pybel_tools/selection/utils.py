# -*- coding: utf-8 -*-

from itertools import combinations

from pybel.constants import FUNCTION, NAMESPACE

__all__ = [
    'get_nodes_by_function',
    'get_triangles',
]


def get_nodes_by_function(graph, function):
    """Get all nodes of a given type.

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param function: The BEL function to filter by
    :type function: str
    :return: An iterable of all BEL nodes with the given function
    :rtype: iter
    """
    for node in graph.nodes_iter():
        if function == graph.node[node][FUNCTION]:
            yield node


def get_nodes_by_function_namespace(graph, function, namespace):
    """Returns an iterator over nodes with the given function and namespace

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param function: The function to filter
    :type function: str
    :param namespace: The namespace to filter
    :type namespace: str
    :return: An iterable over nodes with the given function and namspace
    :rtype: iter
    """
    for node, data in graph.nodes(data=True):
        if function == data[FUNCTION] and NAMESPACE in data and data[NAMESPACE] == namespace:
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


def get_leaves_by_type(graph, function=None, prune_threshold=1):
    """Returns an iterable over all nodes in graph (in-place) with only a connection to one node. Useful for gene and
     RNA. Allows for optional filter by function type.

    :param graph: a BEL network
    :type graph: pybel.BELGraph
    :param function: If set, filters by the node's function from :code:`pybel.constants` like :code:`GENE`, :code:`RNA`,
                     :code:`PROTEIN`, or :code:`BIOPROCESS`
    :type function: str
    :param prune_threshold: Removes nodes with less than or equal to this number of connections. Defaults to :code:`1`
    :type prune_threshold: int
    :return: An iterable over nodes with only a connection to one node
    :rtype: iter
    """
    for node, data in graph.nodes_iter(data=True):
        if len(graph.adj[node]) <= prune_threshold and (not function or function == data.get(FUNCTION)):
            yield node
