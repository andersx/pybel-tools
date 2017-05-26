# -*- coding: utf-8 -*-

import networkx as nx

from .. import pipeline

__all__ = [
    'ensure_node_from_universe',
    'remove_isolated_nodes',
]


@pipeline.uni_in_place_mutator
def ensure_node_from_universe(universe, graph, node, raise_for_missing=False):
    """Makes sure that the subgraph has the given node
    
    :param pybel.BELGraph universe: The universe of all knowledge
    :param pybel.BELGraph graph: The target BEL graph
    :param node: A BEL node
    :param raise_for_missing: Should an error be thrown if the given node is not in the universe?
    :type raise_for_missing: bool
    """
    if raise_for_missing and node not in universe:
        raise ValueError('{} not in {}'.format(node, universe.name))

    if node not in graph:
        graph.add_node(node, attr_dict=universe.node[node])


@pipeline.in_place_mutator
def remove_isolated_nodes(graph):
    """Removes isolated nodes from the network

    :param pybel.BELGraph graph: A BEL graph
    """
    nodes = list(nx.isolates(graph))
    graph.remove_nodes_from(nodes)
