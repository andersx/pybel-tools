# -*- coding: utf-8 -*-

from pybel.constants import RELATION
from ..summary.edge_summary import get_consistent_edges
from ..utils import list_edges

__all__ = [
    'left_merge',
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


def collapse_consistent_edges(graph):
    """Collapses consistient edges together

    .. warning:: This operation doesn't preserve evidences

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    """

    for u, v in get_consistent_edges(graph):
        rel = [d[RELATION] for d in graph.edge[u][v].values()][0]
        graph.remove_edges_from(list_edges(graph, u, v))
        graph.add_edge(u, v, attr_dict={RELATION: rel})
