# -*- coding: utf-8 -*-

from .. import pipeline


@pipeline.uni_in_place_mutator
def ensure_node_from_universe(universe, graph, node, raise_for_missing=False):
    """Makes sure that the subgraph has the given node
    
    :param universe: The universe of all knowledge
    :type universe: pybel.BELGraph
    :param graph: The target BEL graph
    :type graph: pybel.BELGraph
    :param node: A BEL node
    :param raise_for_missing: Should an error be thrown if the given node is not in the universe?
    :type raise_for_missing: bool
    """
    if raise_for_missing and node not in universe:
        raise ValueError('{} not in {}'.format(node, universe.name))

    if node not in graph:
        graph.add_node(node, attr_dict=universe.node[node])
