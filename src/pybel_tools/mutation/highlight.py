# -*- coding: utf-8 -*-

NODE_HIGHLIGHT = 'pybel_highlight'
NODE_HIGHLIGHT_DEFAULT_COLOR = 'red'
EDGE_HIGHLIGHT = 'pybel_highlight'
EDGE_HIGHLIGHT_DEFAULT_COLOR = 'red'


def highlight_nodes(graph, nodes, color=None):
    """Adds a highlight tag to the given nodes
    
    :param graph: A BEL graph 
    :type graph: pybel.BELGraph
    :param nodes: The nodes to add a highlight tag on
    :type nodes: iter[tuple]
    :param color: The color to highlight (use something that works with CSS)
    :type color: str
    """
    for node in nodes:
        graph.node[node][NODE_HIGHLIGHT] = NODE_HIGHLIGHT_DEFAULT_COLOR if color is None else color


def remove_highlight_nodes(graph, nodes=None):
    """Removes the highlight from the given nodes, or all nodes if none given"""
    for node in graph.nodes_iter() if nodes is None else nodes:
        if NODE_HIGHLIGHT in graph.node[node]:
            del graph.node[node][NODE_HIGHLIGHT]


def highlight_edges(graph, edges, color=None):
    """Adds a highlight tag to the given edges
    
    :param graph: A BEL graph 
    :type graph: pybel.BELGraph
    :param edges: The edges (4-tuples of u,v,k,d) to add a highlight tag on
    :type edges: iter[tuple]
    :param color: The color to highlight (use something that works with CSS)
    :type color: str
    :return: 
    """
    for u, v, k, d in edges:
        graph.edge[u][v][k][EDGE_HIGHLIGHT] = EDGE_HIGHLIGHT_DEFAULT_COLOR if color is None else color


def remove_highlight_edges(graph, edges=None):
    """Removes the highlight from the given edges, or all edges if none given
    
    :param graph: A BEL graph 
    :type graph: pybel.BELGraph
    :param edges: The edges (4-tuple of u,v,k,d) to remove the highlight from)
    :type edges: iter[tuple]
    """
    for u, v, k, d in graph.edges_iter(keys=True, data=True) if edges is None else edges:
        if EDGE_HIGHLIGHT in graph.edge[u][v][k]:
            del graph.edge[u][v][k][EDGE_HIGHLIGHT]


def highlight_subgraph(universe, graph):
    """Highlights all nodes/edges in the universe that in the given graph
    
    :type universe: pybel.BELGraph
    :type graph: pybel.BELGraph
    """
    highlight_nodes(universe, graph.nodes())
    highlight_edges(universe, graph.edges)


def remove_highlight_subgraph(graph, subgraph):
    """Removes the highlight from all nodes/edges in the universe that in the given graph

    :type universe: pybel.BELGraph
    :type graph: pybel.BELGraph
    """
    remove_highlight_nodes(graph, subgraph.nodes_iter())
    remove_highlight_edges(graph, subgraph.edges_iter(data=True, keys=True))
