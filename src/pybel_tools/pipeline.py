"""

This module assists in running complex workflows on BEL graphs

"""

from pybel import BELGraph


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
