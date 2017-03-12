# -*- coding: utf-8 -*-

from ..filters import keep_node_permissive
from ..mutation.merge import left_merge
from ..selection import get_upstream_causal_subgraph

__all__ = [
    'expand_upstream_causal_subgraph',
    'expand_internal_causal',
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


def expand_internal_causal(graph, subgraph, target_filter=None):
    """Adds causal edges between entities in the subgraph

    :param graph: The full graph
    :type graph: pybel.BELGraph
    :param subgraph: A subgraph to find the upstream information
    :type subgraph: pybel.BELGraph
    :param target_filter: A predicate for target nodes (graph, node) -> bool. Could be used to not match nodes that
                          are the causal root for a tree that's being grown
    :type target_filter: lambda

    """
    if target_filter is None:
        target_filter = keep_node_permissive

    raise NotImplementedError('Not finished implementing')
