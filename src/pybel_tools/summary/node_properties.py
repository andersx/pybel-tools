"""

This module contains functions that calculate properties of nodes

"""

from pybel.constants import RELATION, CAUSAL_RELATIONS, FUNCTION


def has_causal_out_edges(graph, node):
    """Gets if the node has causal out edges

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param node: A node
    :type node: tuple
    :return: If the node has causal out edges
    :rtype: bool
    """
    return any(d[RELATION] in CAUSAL_RELATIONS for _, _, d in graph.out_edges_iter(node, data=True))


def has_causal_in_edges(graph, node):
    """Gets if the node has causal in edges

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param node: A node
    :type node: tuple
    :return: If the node has causal in edges
    :rtype: bool
    """
    return any(d[RELATION] in CAUSAL_RELATIONS for _, _, d in graph.in_edges_iter(node, data=True))


def get_causal_out_edges(graph, node):
    """Gets the out-edges to the given node that are causal

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param node: A node
    :type node: tuple
    :return: A set of (source, target) pairs where the source is the given node
    :rtype: set
    """

    return {(u, v) for u, v, d in graph.out_edges_iter(node, data=True) if d[RELATION] in CAUSAL_RELATIONS}


def get_causal_in_edges(graph, node):
    """Gets the in-edges to the given node that are causal

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param node: A node
    :type node: tuple
    :return: A set of (source, target) pairs where the target is the given node
    :rtype: set
    """
    return {(u, v) for u, v, d in graph.in_edges_iter(node, data=True) if d[RELATION] in CAUSAL_RELATIONS}


def get_source_abundances(graph, function):
    """Returns a set of all ABUNDANCE nodes that have an in-degree of 0, which likely means that it is an external
    perterbagen and is not known to have any causal origin from within the biological system.

    These nodes are useful to identify because they generally don't provide any mechanistic insight.

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param function: The function to filter by
    :type function: str
    :return: A set of source nodes
    :rtype: set
    """
    return {n for n, d in graph.nodes_iter(data=True) if
            d[FUNCTION] == function and not has_causal_in_edges(graph, n) and has_causal_out_edges(graph, n)}


def get_central_abundances(graph, function):
    """Returns a set of all ABUNDANCE nodes that have both an in-degree > 0 and out-degree > 0. This means
    that they are an integral part of a pathway, since they are both produced and consumed.

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param function: The function to filter by
    :type function: str
    :return: A set of central ABUNDANCE nodes
    :rtype: set
    """
    result = set()

    for n, d in graph.nodes_iter(data=True):
        if d[FUNCTION] == function and has_causal_in_edges(graph, n) and has_causal_out_edges(graph, n):
            result.add(n)

    return result


def get_sink_abundances(graph, function):
    """Returns a set of all ABUNDANCE nodes that have an causal out-degree of 0, which likely means that the knowledge
    assembly is incomplete, or there is a curation error.

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param function: The function to filter by
    :type function: str
    :return: A set of sink ABUNDANCE nodes
    :rtype: set
    """
    return {n for n, d in graph.nodes_iter(data=True) if
            d[FUNCTION] == function and not has_causal_out_edges(graph, n) and has_causal_in_edges(graph, n)}