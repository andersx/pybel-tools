# -*- coding: utf-8 -*-

from pybel.constants import FUNCTION, NAMESPACE, GENE, RNA
from ..filters.node_filters import filter_nodes
from ..summary.edge_summary import get_inconsistent_edges
from ..utils import list_edges

__all__ = [
    'remove_nodes_by_namespace',
    'prune_by_namespace',
    'prune_by_type',
    'prune',
    'remove_filtered_nodes',
    'remove_inconsistent_edges',
]


def remove_nodes_by_namespace(graph, function, namespace):
    """Removes nodes with the given function and namespace

    :param graph: A BEL graph
    :type: graph: pybel.BELGraph
    :param function: The function to filter
    :param namespace: The namespace to filter
    """
    remove_nodes = []
    for node, data in graph.nodes(data=True):
        if data[FUNCTION] == function and data[NAMESPACE] == namespace:
            remove_nodes.append(node)

    graph.remove_nodes_from(remove_nodes)


def prune_by_namespace(graph, function, namespace):
    """Prunes all nodes of a given namespace

    This might be useful to exclude information learned about distant species, such as excluding all information
    from MGI and RGD in diseases where mice and rats don't give much insight to the human disease mechanism.

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param function: The function to filter
    :type function: str
    :param namespace: The namespace to filter
    :type namespace: str
    """
    to_prune = []

    for node, data in graph.nodes_iter(data=True):
        if function == data[FUNCTION] and NAMESPACE in data and namespace == data[NAMESPACE]:
            to_prune.append(node)

    graph.remove_nodes_from(to_prune)


def prune_by_type(graph, function=None, prune_threshold=1):
    """Removes all nodes in graph (in-place) with only a connection to one node. Useful for gene and RNA.
    Allows for optional filter by function type.


    :param graph: a BEL network
    :type graph: pybel.BELGraph
    :param function: If set, filters by the node's function from :code:`pybel.constants` like :code:`GENE`, :code:`RNA`,
                     :code:`PROTEIN`, or :code:`BIOPROCESS`
    :type function: str
    :param prune_threshold: Removes nodes with less than or equal to this number of connections. Defaults to :code:`1`
    :type prune_threshold: int
    :return: The number of nodes pruned
    :rtype: int
    """
    to_prune = []

    for gene, data in graph.nodes_iter(data=True):
        if len(graph.adj[gene]) <= prune_threshold and (not function or function == data.get(FUNCTION)):
            to_prune.append(gene)

    graph.remove_nodes_from(to_prune)

    return len(to_prune)


def prune(graph):
    """Prunes genes, then RNA, in place

    :param graph: a BEL network
    :type graph: pybel.BELGraph

    """
    prune_by_type(graph, GENE)
    prune_by_type(graph, RNA)


def remove_filtered_nodes(graph, *filters):
    """Removes nodes passing the given filters

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param filters: a list of filters
    :type filters: list
    """
    nodes_to_remove = list(filter_nodes(graph, *filters))
    graph.remove_nodes_from(nodes_to_remove)


def remove_inconsistent_edges(graph):
    """Remove all edges between node paris with consistent edges.

    This is the all-or-nothing approach. It would be better to do more careful investigation of the evidences.

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    """
    for u, v in get_inconsistent_edges(graph):
        graph.remove_edges_from(list_edges(graph, u, v))
