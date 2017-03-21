# -*- coding: utf-8 -*-

"""This module contains convenient functions for removing nodes/edges that are returned from selection functions"""

from ..filters.node_filters import filter_nodes
from ..selection.leaves import get_gene_leaves, get_rna_leaves
from ..selection.utils import get_leaves_by_type, get_nodes_by_function_namespace
from ..summary.edge_summary import get_inconsistent_edges
from ..utils import all_edges_iter

__all__ = [
    'remove_nodes_by_namespace',
    'remove_leaves_by_type',
    'prune',
    'remove_filtered_nodes',
    'remove_inconsistent_edges',
]


def remove_nodes_by_namespace(graph, function, namespace):
    """Removes nodes with the given function and namespace.

    This might be useful to exclude information learned about distant species, such as excluding all information
    from MGI and RGD in diseases where mice and rats don't give much insight to the human disease mechanism.

    :param graph: A BEL graph
    :type: graph: pybel.BELGraph
    :param function: The function to filter
    :type function: str
    :param namespace: The namespace to filter
    :type namespace: str
    """
    nodes = list(get_nodes_by_function_namespace(graph, function, namespace))
    graph.remove_nodes_from(nodes)


def remove_leaves_by_type(graph, function=None, prune_threshold=1):
    """Removes all nodes in graph (in-place) with only a connection to one node. Useful for gene and RNA.
    Allows for optional filter by function type.


    :param graph: a BEL network
    :type graph: pybel.BELGraph
    :param function: If set, filters by the node's function from :code:`pybel.constants` like :code:`GENE`, :code:`RNA`,
                     :code:`PROTEIN`, or :code:`BIOPROCESS`
    :type function: str
    :param prune_threshold: Removes nodes with less than or equal to this number of connections. Defaults to :code:`1`
    :type prune_threshold: int
    """
    nodes = list(get_leaves_by_type(graph, function=function, prune_threshold=prune_threshold))
    graph.remove_nodes_from(nodes)


def prune(graph):
    """Prunes genes, then RNA, in place

    :param graph: a BEL network
    :type graph: pybel.BELGraph
    """
    gene_leaves = list(get_gene_leaves(graph))
    graph.remove_nodes_from(gene_leaves)

    rna_leaves = list(get_rna_leaves(graph))
    graph.remove_nodes_from(rna_leaves)


def remove_filtered_nodes(graph, *filters):
    """Removes nodes passing the given filters

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param filters: a list of filters
    :type filters: list
    """
    nodes = list(filter_nodes(graph, *filters))
    graph.remove_nodes_from(nodes)


def remove_inconsistent_edges(graph):
    """Remove all edges between node paris with consistent edges.

    This is the all-or-nothing approach. It would be better to do more careful investigation of the evidences during
    curation.

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    """
    for u, v in get_inconsistent_edges(graph):
        edges = list(all_edges_iter(graph, u, v))
        graph.remove_edges_from(edges)
