# -*- coding: utf-8 -*-

"""

This module provides functions for generating subgraphs based around a single node, most likely a biological process.

Subgraphs induced around biological processes should prove to be subgraphs of the NeuroMMSig/canonical mechanisms
and provide an even more rich mechanism inventory.

"""

from pybel.constants import BIOPROCESS
from . import pipeline
from .mutation.deletion import remove_inconsistent_edges
from .mutation.expansion import get_upstream_causal_subgraph, expand_upstream_causal_subgraph
from .mutation.merge import collapse_consistent_edges
from .selection.leaves import get_unweighted_upstream_leaves
from .selection.utils import get_nodes_by_function

__all__ = [
    'remove_unweighted_leaves',
    'remove_unweighted_sources',
    'generate_mechanism',
    'generate_bioprocess_mechanisms',
]


@pipeline.in_place_mutator
def remove_unweighted_leaves(graph, key):
    """

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param key: The key in the node data dictionary representing the experimental data
    :type key: str
    """
    unweighted_leaves = list(get_unweighted_upstream_leaves(graph, key))
    graph.remove_nodes_from(unweighted_leaves)


def is_unweighted_source(graph, node, key):
    """
    
    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param node: A BEL node
    :type node: tuple
    :param key: The key in the node data dictionary representing the experimental data
    :type key: str
    """
    return graph.in_degree(node) == 0 and key not in graph.node[node]


def get_unweighted_sources(graph, key):
    """Gets unannotated nodes on the periphery of the subgraph

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param key: The key in the node data dictionary representing the experimental data
    :type key: str
    :return: An iterator over BEL nodes that are unannotated and on the periphery of this subgraph
    :rtype: iter
    """
    for node in graph.nodes_iter():
        if is_unweighted_source(graph, node, key):
            yield node


@pipeline.in_place_mutator
def remove_unweighted_sources(graph, key):
    """Prunes unannotated nodes on the periphery of the subgraph

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param key: The key in the node data dictionary representing the experimental data
    :type key: str
    """
    nodes = list(get_unweighted_sources(graph, key))
    graph.remove_nodes_from(nodes)


@pipeline.in_place_mutator
def prune_mechanism_by_data(graph, key):
    """Removes all leaves and source nodes that don't have weights. Is a thin wrapper around 
    :func:`remove_unweighted_leaves` and :func:`remove_unweighted_sources`

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param key: The key in the node data dictionary representing the experimental data. If none, does not prune
                unannotated nodes after generation
    :type key: str
    
    Equivalent to:
    
    >>> remove_unweighted_leaves(graph, key)
    >>> remove_unweighted_sources(graph, key)
    """
    remove_unweighted_leaves(graph, key)
    remove_unweighted_sources(graph, key)


@pipeline.mutator
def generate_mechanism(graph, node, key=None):
    """Generates a mechanistic subgraph upstream of the given node

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param node: The target BEL node for generation
    :type node: tuple
    :param key: The key in the node data dictionary representing the experimental data. If none, does not prune
                unannotated nodes after generation
    :type key: str
    :return: A subgraph grown around the target BEL node
    :rtype: pybel.BELGraph
    """
    subgraph = get_upstream_causal_subgraph(graph, node)
    expand_upstream_causal_subgraph(graph, subgraph)
    remove_inconsistent_edges(subgraph)
    collapse_consistent_edges(subgraph)

    if key is not None:
        prune_mechanism_by_data(subgraph, key)

    return subgraph


def generate_bioprocess_mechanisms(graph, key=None):
    """Generates a mechanistic subgraph for each biological process in the graph using :func:`generate_mechanism`

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param key: The key in the node data dictionary representing the experimental data. If none, does not prune
                unannotated nodes after generation
    :type key: str
    :return: A dictionary from {str bioprocess node: BELGraph candidate mechanism}
    :rtype: dict[tuple, pybel.BELGraph]
    """
    return {bp: generate_mechanism(graph, bp, key=key) for bp in get_nodes_by_function(graph, BIOPROCESS)}
