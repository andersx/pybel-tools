# -*- coding: utf-8 -*-

"""This module contains utilities to help merge data"""

from pybel.constants import RELATION
from ..summary.edge_summary import get_consistent_edges
from ..utils import all_edges_iter

__all__ = [
    'left_merge',
    'right_merge',
    'collapse_consistent_edges',
]


def left_merge(g, h):
    """Adds nodes and edges from H to G, in-place for G

    :param g: A BEL Graph
    :type g: pybel.BELGraph
    :param h: A BEL Graph
    :type h: pybel.BELGraph
    """
    for node, data in h.nodes_iter(data=True):
        if node not in g:
            g.add_node(node, data)

    for u, v, k, d in h.edges_iter(keys=True, data=True):
        if k < 0:  # unqualified edge that's not in G yet
            if v not in g.edge[u] or k not in g.edge[u][v]:
                g.add_edge(u, v, key=k, attr_dict=d)
        elif v not in g.edge[u]:
            g.add_edge(u, v, attr_dict=d)
        elif any(0 <= gk and d == gd for gk, gd in g.edge[u][v].items()):
            continue
        else:
            g.add_edge(u, v, attr_dict=d)


def right_merge(g, h):
    """Performs :func:`left_merge` on the arguments in the opposite order.

    :param g: A BEL Graph
    :type g: pybel.BELGraph
    :param h: A BEL Graph
    :type h: pybel.BELGraph
    """
    left_merge(h, g)


def collapse_consistent_edges(graph):
    """Collapses consistent edges together

    .. warning:: This operation doesn't preserve evidences or other annotations

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    """
    for u, v in get_consistent_edges(graph):
        rel = [d[RELATION] for d in graph.edge[u][v].values()][0]
        edges = list(all_edges_iter(graph, u, v))
        graph.remove_edges_from(edges)
        graph.add_edge(u, v, attr_dict={RELATION: rel})
