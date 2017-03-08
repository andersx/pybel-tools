"""

This module contains a set of default functions for filtering nodes and building node filtering functions

"""

from pybel.constants import FUNCTION, PATHOLOGY, OBJECT, SUBJECT, MODIFIER, ACTIVITY


def keep_node_permissive(graph, node):
    """A default node filter that is true for all nodes

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param node: The node
    :type node: tuple
    :return: True
    :rtype: bool
    """
    return True


def function_filter_builder(function):
    """Builds a filter that fails on nodes of the fiven function

    :param function: A BEL Function
    :type function: str
    :return: A node filter (graph, node) -> bool
    :rtype: lambda
    """

    def node_filter(graph, node):
        return graph.node[node][FUNCTION] != function

    return node_filter


def exclusion_filter_builder(*nodes):
    """Builds a filter that fails on nodes in the fiven list

    :param nodes: A list of nodes
    :type nodes: list
    :return: A node filter (graph, node) -> bool
    :rtype: lambda
    """

    def node_filter(graph, node):
        return all(node != n for n in nodes)

    return node_filter


pathology_filter = function_filter_builder(PATHOLOGY)


def keep_molecularly_active(graph, node):
    """Returns true if the given node has a known molecular activity

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param node: A BEL node
    :type node: tuple
    :return: If the node has a known molecular activity
    :rtype: bool
    """
    for _, _, d in graph.in_edges(node):
        if OBJECT in d and MODIFIER in d[OBJECT] and d[OBJECT][MODIFIER] == ACTIVITY:
            return True

    for _, _, d in graph.out_edges(node):
        if SUBJECT in d and MODIFIER in d[SUBJECT] and d[SUBJECT][MODIFIER] == ACTIVITY:
            return True

    return False


def keep_node(graph, node, super_nodes=None):
    """A default node filter for removing unwanted nodes in an analysis.

    This function returns false for nodes that have PATHOLOGY or are on a pre-defined blacklist. This can be most
    easily used with :py:func:`functools.partial`:

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param node: The node to check if it should be kepy
    :type node: tuple
    :param super_nodes: A list of nodes to automatically throw out
    :type super_nodes: list of tuples
    :return: Should the node be kept?
    :rtype: bool


    >>> from functools import partial
    >>> from pybel.constants import GENE
    >>> from pybel_tools.node_filters import keep_node
    >>> cool_filter = partial(keep_node, super_nodes={(GENE, 'HGNC', 'APP')})
    """

    if graph.node[node][FUNCTION] == PATHOLOGY:
        return False

    if super_nodes and node in super_nodes:
        return False

    return True


def filter_concatenator(*filters):
    """Concatenates multiple node filters to a new filter that requires all filters to be met

    :param filters: a list of predicates (graph, node) -> bool
    :type filters: list
    :return: A combine filter (graph, node) -> bool
    :rtype: lambda
    """

    def new_filter(graph, node):
        return all(f(graph, node) for f in filters)

    return new_filter


def apply_node_filters(graph, *filters):
    """Applies a set of filters to the nodes iterator of a BEL graph

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param filters: a list of filters
    :type filters: list
    :return: An iterable of nodes that pass all filters
    :rtype: iter
    """
    if not filters:
        return graph.nodes_iter()

    return filter(filter_concatenator(*filters), graph.nodes_iter())
