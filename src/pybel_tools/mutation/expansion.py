# -*- coding: utf-8 -*-

from ..mutation.merge import left_merge
from ..selection import get_upstream_causal_subgraph

__all__ = [
    'expand_upstream_causal_subgraph'
]


def expand_upstream_causal_subgraph(graph, subgraph):
    """Adds the upstream causal relations to the given subgraph

    :param graph: The full graph
    :type graph: pybel.BELGraph
    :param subgraph: A subgraph to find the upstream information
    :type graph: pybel.BELGraph
    """
    for node in subgraph.nodes():
        upstream = get_upstream_causal_subgraph(graph, node)

        left_merge(subgraph, upstream)
