# -*- coding: utf-8 -*-

"""This module assists in running complex workflows on BEL graphs"""

from pybel import BELGraph
from .summary.export import info_list

OPERATION_PROVENANCE = 'operation_provenance'


# TODO make more strict for non-in place operations so it's possible to perform a functional "reduce"
def transform(graph, *transformations):
    """Applies a series of transformations to a graph

    This function mixes the ability to perform in-place and copying operations, so it's
    a good idea to assume the original graph isn't stable after applying this function.

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :return: A transformed BEL graph
    :rtype: pybel.BELGraph
    """

    current_graph = graph

    for transformation in transformations:
        result = transformation(current_graph)
        if isinstance(result, BELGraph):
            current_graph = result

    return current_graph


def add_operation(graph, operation_info):
    """Adds annotations to the graph about what transformations were applied

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param operation_info: A dictionary containing information about the function that was applied
    :type operation_info: dict
    """
    if OPERATION_PROVENANCE not in graph.graph:
        graph.graph[OPERATION_PROVENANCE] = []
    graph.graph[OPERATION_PROVENANCE].append(operation_info)


def summarize_operation_list(graph, graph_function):
    """Applies an operation to the graph then returns a list with the information about the change in the
    graph's properties.

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param graph_function: A mutation function that takes (graph, ) -> None
    :type graph_function: lambda
    :return: A list of the change in each aspect of the graph
    :rtype: list
    """
    pre_list = info_list(graph)
    graph_function(graph)
    post_list = info_list(graph)

    result = [pre_list[0]]

    for (k, before), (_, after) in zip(pre_list, post_list):
        result.append((k, after - before))

    return result
