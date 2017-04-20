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
    'get_correlation_graph',
    'get_correlation_triangles',
    'get_separate_unstable_correlation_triples',
    'get_mutually_unstable_correlation_triples',
    'jens_transformation_alpha',
    'jens_transformation_beta',
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
    """
    
    :param pybel.BELGraph graph: 
    :return: 
    :rtype: networkx.Graph
    """
    result = Graph()

    for u, v, d in graph.edges_iter(data=True):
        if d[RELATION] not in CORRELATIVE_RELATIONS:
            continue

        if not result.has_edge(u, v):
            result.add_edge(u, v, **{d[RELATION]: True})

        elif d[RELATION] not in result.edge[u][v]:
            log.warning('broken correlation relation for %s, %s', u, v)
            result.edge[u][v][d[RELATION]] = True
            result.edge[v][u][d[RELATION]] = True

    return result


def get_correlation_triangles(correlation_graph):
    """Yields all triangles pointed by the given node

    :param correlation_graph: A correlation graph
    :type correlation_graph: networkx.Graph
    """
    results = set()

    for n in correlation_graph.nodes_iter():
        for u, v in combinations(correlation_graph.edge[n], 2):
            if correlation_graph.has_edge(u, v):
                results.add(tuple(sorted([n, u, v], key=str)))

    return results


def get_separate_unstable_correlation_triples(graph):
    """Find all triples of nodes A, B, C such that ``A pos B``, ``A pos C``, and ``B neg C``

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
    """Find all triples of nodes A, B, C such that ``A neg B``, ``B neg C``, and ``C neg A``.

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :return:
    :rtype: iter[tuple]
    """
    cg = get_correlation_graph(graph)

    for a, b, c in get_correlation_triangles(cg):
        if all(NEGATIVE_CORRELATION in x for x in (cg.edge[a][b], cg.edge[b][c], cg.edge[a][c])):
            yield a, b, c


def jens_transformation_alpha(graph):
    """Applys Jens' transformation (Type 1) to the graph

    1. Induce subgraph over causal + correlative edges
    2. Transform edges by the following rules:
        - increases => increases
        - decreases => backwards increases
        - positive correlation => two way increases
        - negative correlation => delete

    - Search for 3-cycles, which now symbolize unstable triplets where A -> B, A -| C and B pos C
    - What do 4-cycles and 5-cycles mean?

    :param pybel.BELGraph graph: A BEL graph
    :rtype: networkx.DiGraph
    """
    result = DiGraph()

    for u, v, k, d in graph.edges_iter(keys=True, data=True):
        relation = d[RELATION]

        if relation == POSITIVE_CORRELATION:
            result.add_edge(u, v)
            result.add_edge(v, u)

        elif relation in CAUSAL_INCREASE_RELATIONS:
            result.add_edge(u, v)

        elif relation in CAUSAL_DECREASE_RELATIONS:
            result.add_edge(v, u)

    for node in result.nodes_iter():
        result.node[node].update(graph.node[node])

    return result


def jens_transformation_beta(graph):
    """Applys Jens' transformation (Type 2) to the graph

    1. Induce subgraph over causal + correlative edges
    2. Transform edges by the following rules:
        - increases => backwards decreases
        - decreases => decreases
        - positive correlation => delete
        - negative correlation => two way decreases

    - Search for 3-cycles, which now symbolize unstable triplets where A -> B, A -| C and B neg C
    - What do 4-cycles and 5-cycles mean?

    :param pybel.BELGraph graph: A BEL graph
    :rtype: networkx.DiGraph
    """
    retult = DiGraph()

    for u, v, k, d in graph.edges_iter(keys=True, data=True):
        relation = d[RELATION]

        if relation == NEGATIVE_CORRELATION:
            retult.add_edge(u, v)
            retult.add_edge(v, u)

        elif relation in CAUSAL_INCREASE_RELATIONS:
            retult.add_edge(v, u)

        elif relation in CAUSAL_DECREASE_RELATIONS:
            retult.add_edge(u, v)

    for node in retult.nodes_iter():
        retult.node[node].update(graph.node[node])

    return retult
