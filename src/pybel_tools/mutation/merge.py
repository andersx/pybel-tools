# -*- coding: utf-8 -*-

__all__ = [
    'left_merge',
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
