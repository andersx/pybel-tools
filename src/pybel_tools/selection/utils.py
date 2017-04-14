# -*- coding: utf-8 -*-

from itertools import combinations

from pybel.constants import FUNCTION
from ..filters.node_filters import function_inclusion_filter_builder, filter_nodes, \
    function_namespace_inclusion_builder, namespace_inclusion_builder

__all__ = [
    'get_nodes_by_function',
    'get_nodes_by_namespace',
    'get_nodes_by_function_namespace',
    'get_triangles',
    'get_leaves_by_type',
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
    return filter_nodes(graph, function_inclusion_filter_builder(function))


def get_nodes_by_namespace(graph, namespace):
    """Returns an iterator over nodes with the given namespace

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param namespace: The namespace to filter
    :type namespace: str
    :return: An iterable over nodes with the given function and namspace
    :rtype: iter
    """
    return filter_nodes(graph, namespace_inclusion_builder(namespace))


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
    return filter_nodes(graph, function_namespace_inclusion_builder(function, namespace))


def get_triangles(graph, node):
    """Yields all triangles pointed by the given node

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param node: The source node
    :type node: tuple
    """
    for a, b in combinations(graph.edge[node], 2):
        if b in graph.edge[a]:
            yield a, b
        if a in graph.edge[b]:
            yield b, a


# FIXME what's up with graph.adj[node]? can use graph.in_degree(node) and graph.out_degree(node) much better
def get_leaves_by_type(graph, function=None, prune_threshold=1):
    """Returns an iterable over all nodes in graph (in-place) with only a connection to one node. Useful for gene and
     RNA. Allows for optional filter by function type.

    :param graph: a BEL network
    :type graph: pybel.BELGraph
    :param function: If set, filters by the node's function from :mod:`pybel.constants` like 
                    :data:`pybel.constants.GENE`, :data:`pybel.constants.RNA`,  :data:`pybel.constants.PROTEIN`, or 
                    :data:`pybel.constants.BIOPROCESS`
    :type function: str
    :param prune_threshold: Removes nodes with less than or equal to this number of connections. Defaults to :code:`1`
    :type prune_threshold: int
    :return: An iterable over nodes with only a connection to one node
    :rtype: iter
    """
    for node, data in graph.nodes_iter(data=True):
        if len(graph.adj[node]) <= prune_threshold and (not function or function == data.get(FUNCTION)):
            yield node
