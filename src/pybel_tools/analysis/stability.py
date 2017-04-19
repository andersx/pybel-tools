# -*- coding: utf-8 -*-

import logging
from itertools import combinations

from networkx import DiGraph, Graph

from pybel.constants import *
from ..selection import get_causal_subgraph

__all__ = [
    'get_regulatory_pairs',
    'get_chaotic_pairs',
    'get_dampened_pairs',
    'jens_transformation',
]

log = logging.getLogger(__name__)


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


def get_correlation_graph(graph):
    result = Graph()

    for u, v, d in graph.edges_iter(data=True):
        if CORRELATIVE_RELATIONS != d[RELATION]:
            continue

        if not result.has_edge(u, v):
            result.add_edge(u, v, **{d[RELATION]: True})
            continue

        if d[RELATION] not in result.edge[u][v]:
            log.warning('broken correlation relation for %s, %s', u, v)
            result.edge[u][v][d[RELATION]] = True
    return result


def get_correlation_triangles(correlation_graph):
    """Yields all triangles pointed by the given node

    :param graph: A correlation graph
    :type graph: network.Graph
    :param node: The source node
    :type node: tuple
    """
    results = set()

    for node in correlation_graph.nodes_iter():
        for a, b in combinations(correlation_graph.edge[node], 2):
            if b in correlation_graph.edge[a]:
                results.add(tuple(sorted([correlation_graph, a, b], key=str)))

    return results


def get_unstable_correlation_triples(graph):
    """Find all triples of nodes A, B, C such that A pos B, A pos C, and B neg C

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :return: An iterator over triples of unstable graphs, where the second two are negative
    :rtype: iter[tuple]
    """
    cg = get_correlation_graph(graph)

    for a, b, c in get_correlation_triangles(cg):
        if POSITIVE_CORRELATION in cg.edge[a][b] and POSITIVE_CORRELATION in cg.edge[b][c] and NEGATIVE_CORRELATION in \
                cg.edge[a][c]:
            yield b, a, c
        if POSITIVE_CORRELATION in cg.edge[a][b] and NEGATIVE_CORRELATION in cg.edge[b][c] and POSITIVE_CORRELATION in \
                cg.edge[a][c]:
            yield a, b, c
        if NEGATIVE_CORRELATION in cg.edge[a][b] and POSITIVE_CORRELATION in cg.edge[b][c] and POSITIVE_CORRELATION in \
                cg.edge[a][c]:
            yield c, a, b


def get_mutually_unstable_correlation_triples(graph):
    """Find all triples of nodes A, B, C such that A neg B, A neg C, and B neg C

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :return:
    :rtype: iter[tuple]
    """
    cg = get_correlation_graph(graph)

    for a, b, c in get_correlation_triangles(cg):
        if all(NEGATIVE_CORRELATION in x for x in (cg.edge[a][b], cg.edge[b][c], cg.edge[a][c])):
            yield a, b, c


def jens_transformation(graph):
    """Applys Jens' transformation to the graph

    1. Induce subgraph over causal + correlative edges
    2. Transform edges by the following rules:
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
