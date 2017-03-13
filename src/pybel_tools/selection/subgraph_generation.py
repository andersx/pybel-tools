# -*- coding: utf-8 -*-

"""

This module provides functions for generating subgraphs based around a single node, most likely a biological process.

Subgraphs induced around biological processes should prove to be subgraphs of the NeuroMMSig/canonical mechanisms
and provide an even more rich mechanism inventory.


"""

from .induce_subgraph import get_upstream_causal_subgraph
from .leaves import get_unweighted_upstream_leaves
from ..mutation.merge import left_merge

__all__ = [
    'expand_upstream_causal_subgraph',
    'remove_unweighted_leaves',
    'remove_unweighted_sources'
]


def expand_upstream_causal_subgraph(graph, subgraph):
    """Adds the upstream causal relations to the given subgraph

    :param graph: The full graph
    :type graph: pybel.BELGraph
    :param subgraph: A subgraph to find the upstream information
    :type subgraph: pybel.BELGraph
    """
    for node in subgraph.nodes():
        upstream = get_upstream_causal_subgraph(graph, node)
        left_merge(subgraph, upstream)


def remove_unweighted_leaves(graph, key):
    """

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param key: The key in the node data dictionary representing the experimental data
    :type key: str
    """
    unweighted_leaves = list(get_unweighted_upstream_leaves(graph, key))
    graph.remove_nodes_from(unweighted_leaves)


def remove_unweighted_sources(graph, key):
    """

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param key: The key in the node data dictionary representing the experimental data
    :type key: str
    """
    for node in graph.nodes():
        if graph.in_degree(node) == 0 and key not in graph.node[node]:
            graph.remove_node(node)
