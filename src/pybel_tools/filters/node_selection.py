# -*- coding: utf-8 -*-

from .node_filters import filter_nodes, function_inclusion_filter_builder, namespace_inclusion_builder, \
    function_namespace_inclusion_builder
from .. import pipeline

__all__ = [
    'get_nodes_by_function',
    'get_nodes_by_namespace',
    'get_nodes_by_function_namespace',
]


@pipeline.in_place_mutator
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


@pipeline.in_place_mutator
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


@pipeline.in_place_mutator
def get_nodes_by_function_namespace(graph, function, namespace):
    """Returns an iterator over nodes with the given function and namespace

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param function: The function to filter
    :type function: str
    :param namespace: The namespace to filter
    :type namespace: str
    :return: An iterable over nodes with the given function and namespace
    :rtype: iter
    """
    return filter_nodes(graph, function_namespace_inclusion_builder(function, namespace))
