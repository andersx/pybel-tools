# -*- coding: utf-8 -*-

from networkx import DiGraph

from pybel.constants import *
from ..selection import get_causal_subgraph

__all__ = [
    'get_regulatory_pairs',
    'get_chaotic_pairs',
    'get_dampened_pairs',
    'jens_transformation',
]


def get_regulatory_pairs(graph):
    """Finds pairs of nodes that have mutual causal edges that are regulating each other

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :return: A set of pairs of nodes with mutual causal edges
    :rtype: set
    """
    cg = get_causal_subgraph(graph)

    results = set()

    for u, v, d in cg.edges_iter(data=True):
        if d[RELATION] not in CAUSAL_INCREASE_RELATIONS:
            continue

        if cg.has_edge(v, u) and any(dd[RELATION] in CAUSAL_DECREASE_RELATIONS for dd in cg.edge[v][u].values()):
            results.add((u, v))

    return results


def get_chaotic_pairs(graph):
    """Finds pairs of nodes that have mutual causal edges that are increasing each other

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :return: A set of pairs of nodes with mutual causal edges
    :rtype: set
    """
    cg = get_causal_subgraph(graph)

    results = set()

    for u, v, d in cg.edges_iter(data=True):
        if d[RELATION] not in CAUSAL_INCREASE_RELATIONS:
            continue

        if cg.has_edge(v, u) and any(dd[RELATION] in CAUSAL_INCREASE_RELATIONS for dd in cg.edge[v][u].values()):
            results.add(tuple(sorted([u, v], key=str)))

    return results


def get_dampened_pairs(graph):
    """Finds pairs of nodes that have mutual causal edges that are decreasing each other

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :return: A set of pairs of nodes with mutual causal edges
    :rtype: set
    """
    cg = get_causal_subgraph(graph)

    results = set()

    for u, v, d in cg.edges_iter(data=True):
        if d[RELATION] not in CAUSAL_DECREASE_RELATIONS:
            continue

        if cg.has_edge(v, u) and any(dd[RELATION] in CAUSAL_DECREASE_RELATIONS for dd in cg.edge[v][u].values()):
            results.add(tuple(sorted([u, v], key=str)))

    return results


# TODO implement
def get_unstable_correlation_triples(graph):
    """Find all triples of nodes A, B, C such that A pos B, A pos C, and B neg C

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :return:
    """
    raise NotImplementedError


# TODO implement
def get_mutually_unstable_correlation_triples(graph):
    """Find all triples of nodes A, B, C such that A neg B, A neg C, and B neg C

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :return:
    """
    raise NotImplementedError


def jens_transformation(graph):
    """Applys Jens' transformation to the graph

    1. Induce subgraph over causal + correlative edges
    2. Transform edges by the following ruls:
        - increases => increases
        - decreases => backwards increases
        - positive correlation => two way increases
        - negative correlation => delete

    - Search for 3-cycles, which now symbolize unstable triplets where A -> B, A -| C and B pos C
    - What do 4-cycles and 5-cycles mean?

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    """

    bg = DiGraph()

    for u, v, k, d in graph.edges_iter(keys=True, data=True):
        relation = d[RELATION]

        if relation == POSITIVE_CORRELATION:
            bg.add_edge(u, v)
            bg.add_edge(v, u)

        elif relation in CAUSAL_INCREASE_RELATIONS:
            bg.add_edge(u, v)

        elif relation in CAUSAL_DECREASE_RELATIONS:
            bg.add_edge(v, u)

    for node in bg.nodes_iter():
        bg.node[node].update(graph.node[node])

    return bg
