# -*- coding: utf-8 -*-

"""

This module contains functions that provide summaries of the edges in a graph

"""

import itertools as itt
from collections import Counter, defaultdict

from pybel.constants import RELATION, ANNOTATIONS, CITATION, CITATION_TYPE, CITATION_REFERENCE
from ..filters.node_filters import keep_node_permissive
from ..utils import get_value_sets, check_has_annotation

__all__ = [
    'count_relations',
    'get_edge_relations',
    'count_unique_relations',
    'count_annotations',
    'get_annotations',
    'get_annotation_values_by_annotation',
    'count_annotation_values',
    'get_annotation_values',
    'count_annotation_values_filtered',
    'is_consistent',
    'get_consistent_edges',
    'get_inconsistent_edges',
    'count_citations',
    'count_citations_by_subgraph',
]


def count_relations(graph):
    """Returns a histogram over all relationships in a graph

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :return: A Counter from {relation type: frequency}
    :rtype: Counter
    """
    return Counter(d[RELATION] for _, _, d in graph.edges_iter(data=True))


def get_edge_relations(graph):
    """Builds a dictionary of {node pair: set of edge types}

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :return: A dictionary of {(node, node): set of edge types}
    :rtype: dict
    """
    edge_relations = defaultdict(set)
    for u, v, d in graph.edges_iter(data=True):
        edge_relations[u, v].add(d[RELATION])
    return edge_relations


def count_unique_relations(graph):
    """Returns a histogram of the different types of relations present in a graph.

    Note: this operation only counts each type of edge once for each pair of nodes

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :return: Counter from {relation type: frequency}
    :rtype: Counter
    """
    return Counter(itt.chain.from_iterable(get_edge_relations(graph).values()))


def count_annotations(graph):
    """Counts how many times each annotation is used in the graph

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :return: A Counter from {annotation key: frequency}
    :rtype: Counter
    """
    return Counter(key for _, _, d in graph.edges_iter(data=True) if ANNOTATIONS in d for key in d[ANNOTATIONS])


def get_annotations(graph):
    """Gets the set of annotations used in the graph

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :return: A set of annotation keys
    :rtype: set
    """
    return set(count_annotations(graph))


def get_annotation_values_by_annotation(graph):
    """Gets the set of values for each annotation used in a BEL Graph

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :return: A dictionary of {annotation key: set of annotation values}
    :rtype: dict
    """
    result = defaultdict(list)

    for _, _, data in graph.edges_iter(data=True):
        if ANNOTATIONS not in data:
            continue

        for key, value in data[ANNOTATIONS].items():
            result[key].append(value)

    return get_value_sets(result)


def count_annotation_values(graph, annotation):
    """Counts in how many edges each annotation appears in a graph

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param annotation: The annotation to count
    :type annotation: str
    :return: A Counter from {annotation value: frequency}
    :rtype: Counter
    """
    return Counter(
        d[ANNOTATIONS][annotation] for _, _, d in graph.edges_iter(data=True) if check_has_annotation(d, annotation))


def get_annotation_values(graph, annotation):
    """Get all values for the given annotation

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param annotation: The annotation to summarize
    :type annotation: str
    :return: A set of all annotation values
    :rtype: set
    """
    return set(count_annotation_values(graph, annotation))


def count_annotation_values_filtered(graph, annotation, source_filter=None, target_filter=None):
    """Counts in how many edges each annotation appears in a graph, but filter out source nodes and target nodes

    See :func:`pybel_tools.utils.keep_node` for a basic filter.

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param annotation: An annotation to count
    :type annotation: str
    :param source_filter: a predicate (graph, node) -> bool for keeping source nodes
    :type source_filter: lambda
    :param target_filter: a predicate (graph, node) -> bool for keeping target nodes
    :type target_filter: lambda
    :return: A Counter from {annotation value: frequency}
    :rtype: Counter
    """
    source_filter = keep_node_permissive if source_filter is None else source_filter
    target_filter = keep_node_permissive if target_filter is None else target_filter

    return Counter(d[ANNOTATIONS][annotation] for u, v, d in graph.edges_iter(data=True) if
                   check_has_annotation(d, annotation) and source_filter(graph, u) and target_filter(graph, v))


def is_consistent(graph, u, v):
    """Returns if the edges between the given nodes are constitient, meaning they all have the same relation

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param u: The source BEL node
    :param v: The target BEL node
    :return: Do the edges between these nodes all have the same relation
    :rtype: bool
    """
    relations = {d[RELATION] for d in graph.edge[u][v].values()}
    return 1 == len(relations)


def get_consistent_edges(graph):
    """Returns an iterator over consistent edges

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :return: An iterator over (source, target) node pairs corresponding to edges with many inconsistent relations
    :rtype: iter
    """
    for u, v in set(graph.edges_iter()):
        if is_consistent(graph, u, v):
            yield u, v


def get_inconsistent_edges(graph):
    """Returns an iterator over inconsistent edges

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :return: An iterator over (source, target) node pairs corresponding to edges with many inconsistent relations
    :rtype: iter
    """
    for u, v in set(graph.edges_iter()):
        if not is_consistent(graph, u, v):
            yield u, v


def count_citations(graph, **annotations):
    """Counts the citations in a graph based on a given filter

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param annotations: The annotation filters to use
    :type annotations: dict
    :return: A counter from {(citation type, citation reference): frequency}
    :rtype: Counter
    """
    citations = defaultdict(set)

    for u, v, d in graph.edges_iter(data=True, **annotations):
        if CITATION not in d:
            continue

        c = d[CITATION]
        citations[u, v].add((c[CITATION_TYPE], c[CITATION_REFERENCE]))

    counter = Counter(itt.chain.from_iterable(citations.values()))

    return counter


def count_citations_by_subgraph(graph, annotation='Subgraph'):
    """Groups the citation counters by subgraphs induced by the annotation

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param annotation: The annotation to use to group the graph
    :type annotation: str
    :return: A dictionary of Counters {subgraph name: Counter from {citation: frequency}}
    """
    citations = defaultdict(lambda: defaultdict(set))
    for u, v, d in graph.edges_iter(data=True):
        if not check_has_annotation(d, annotation) or CITATION not in d:
            continue

        c = d[CITATION]
        k = d[ANNOTATIONS][annotation]

        citations[k][u, v].add((c[CITATION_TYPE], c[CITATION_REFERENCE]))

    return {k: Counter(itt.chain.from_iterable(v.values())) for k, v in citations.items()}
