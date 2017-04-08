# -*- coding: utf-8 -*-


import itertools as itt
from itertools import chain

import networkx as nx
from networkx import single_source_shortest_path, single_source_dijkstra_path

__all__ = [
    'get_nodes_in_shortest_paths',
    'get_nodes_in_dijkstra_paths',
    'get_shortest_directed_path_between_subgraphs',
    'get_shortest_undirected_path_between_subgraphs',
]


def get_nodes_in_shortest_paths(graph, nodes, cutoff=None):
    """Gets a list of all the nodes on the shortest paths between nodes in the BEL graph with
    :func:`networkx.all_pairs_shortest_path`

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param nodes: The list of nodes to use to use to find all shortest paths
    :type nodes: iter
    :param cutoff:  Depth to stop the search. Only paths of length <= cutoff are returned.
    :type cutoff: int
    :return: A set of nodes appearing in the shortest paths between nodes in the BEL graph
    :rtype: set

    .. note:: This can be trivially parallelized using :func:`networkx.single_source_shortest_path`
    """
    return set(chain.from_iterable(single_source_shortest_path(graph, n, cutoff=cutoff) for n in nodes))


def get_nodes_in_dijkstra_paths(graph, nodes, cutoff=None, weight='weight'):
    """Gets a list of all the nodes on the shortest paths between nodes in the BEL graph with
    :func:`networkx.all_pairs_dijkstra_path`

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param nodes: The list of nodes to use to use to find all shortest paths
    :type nodes: iter
    :param cutoff:  Depth to stop the search. Only paths of length <= cutoff are returned.
    :type cutoff: int
    :param weight: Edge data key corresponding to the edge weight
    :type weight: str
    :return: A set of nodes appearing in the weighted shortest paths between nodes in the BEL graph
    :rtype: set

    .. note:: This can be trivially parallelized using :func:`networkx.single_source_dijkstra_path`
    """
    return set(chain.from_iterable(single_source_dijkstra_path(graph, n, cutoff=cutoff, weight=weight) for n in nodes))


# TODO consider all shortest paths?
def _get_shortest__path_between_subgraphs_helper(graph, a, b):
    """Calculate the shortest path that occurs between two disconnected subgraphs A and B going through nodes in
    the source graph

    :param graph: A graph
    :type graph: nx.MultiGraph
    :param a: A subgraph of :code:`graph`, disjoint from :code:`b`
    :type a: nx.MultiGraph
    :param b: A subgraph of :code:`graph`, disjoint from :code:`a`
    :type b: nx.MultiGraph
    :return: A list of the shortest paths between the two subgraphs
    :rtype: list
    """
    shortest_paths = []

    for na, nb in itt.product(a.nodes_iter(), b.nodes_iter()):
        a_b_shortest_path = nx.shortest_path(graph, na, nb)
        shortest_paths.append(a_b_shortest_path)

        b_a_shortest_path = nx.shortest_path(graph, nb, na)
        shortest_paths.append(b_a_shortest_path)

    min_len = min(map(len, shortest_paths))
    return [p for p in shortest_paths if len(p) == min_len]


def get_shortest_directed_path_between_subgraphs(graph, a, b):
    """Calculate the shortest path that occurs between two disconnected subgraphs A and B going through nodes in
    the source graph

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param a: A subgraph of :code:`graph`, disjoint from :code:`b`
    :type a: pybel.BELGraph
    :param b: A subgraph of :code:`graph`, disjoint from :code:`a`
    :type b: pybel.BELGraph
    :return: A list of the shortest paths between the two subgraphs
    :rtype: list
    """
    return _get_shortest__path_between_subgraphs_helper(graph, a, b)


def get_shortest_undirected_path_between_subgraphs(graph, a, b):
    """Get the shortest path between two disconnected subgraphs A and B, disregarding directionality of edges in graph

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param a: A subgraph of :code:`graph`, disjoint from :code:`b`
    :type a: pybel.BELGraph
    :param b: A subgraph of :code:`graph`, disjoint from :code:`a`
    :type b: pybel.BELGraph
    :return: A list of the shortest paths between the two subgraphs
    :rtype: list
    """
    ug = graph.to_undirected()
    return _get_shortest__path_between_subgraphs_helper(ug, a, b)
