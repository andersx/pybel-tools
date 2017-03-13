# -*- coding: utf-8 -*-

"""

This module provides functions for generating subgraphs based around a single node, most likely a biological process.

Subgraphs induced around biological processes should prove to be subgraphs of the NeuroMMSig/canonical mechanisms
and provide an even more rich mechanism inventory.


"""

from .leaves import get_unweighted_upstream_leaves

__all__ = [
    'remove_unweighted_leaves',
    'remove_unweighted_sources'
]


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
