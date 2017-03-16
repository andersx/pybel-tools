# -*- coding: utf-8 -*-


from itertools import chain

from networkx import single_source_shortest_path, single_source_dijkstra_path

__all__ = [
    'get_nodes_in_shortest_paths',
    'get_nodes_in_dijkstra_paths'
]


def get_nodes_in_shortest_paths(graph, nodes, cutoff=None):
    """Gets a list of all the nodes on the shortest paths between nodes in the BEL graph with
    :func:`networkx.all_pairs_shortest_path`

    .. note:: This can be trivially parallelized using :func:`networkx.single_source_shortest_path`

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param nodes: The list of nodes to use to use to find all shortest paths
    :type nodes: iter
    :param cutoff:  Depth to stop the search. Only paths of length <= cutoff are returned.
    :type cutoff: int
    :return: A set of nodes appearing in the shortest paths between nodes in the BEL graph
    :rtype: set
    """
    return set(chain.from_iterable(single_source_shortest_path(graph, n, cutoff=cutoff) for n in nodes))


def get_nodes_in_dijkstra_paths(graph, nodes, cutoff=None, weight='weight'):
    """Gets a list of all the nodes on the shortest paths between nodes in the BEL graph with
    :func:`networkx.all_pairs_dijkstra_path`

    .. note:: This can be trivially parallelized using :func:`networkx.single_source_dijkstra_path`

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
    """
    return set(chain.from_iterable(single_source_dijkstra_path(graph, n, cutoff=cutoff, weight=weight) for n in nodes))
