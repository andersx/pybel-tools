# -*- coding: utf-8 -*-

"""This module contains functions that provide summaries of the edges in a graph"""

import itertools as itt
from collections import Counter, defaultdict

from pybel.constants import RELATION, ANNOTATIONS, FUNCTION, PATHOLOGY, CAUSAL_INCREASE_RELATIONS, \
    CAUSAL_DECREASE_RELATIONS, CAUSES_NO_CHANGE
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
    'get_all_relations',
    'pair_is_consistent',
    'get_consistent_edges',
    'pair_has_contradiction',
    'get_inconsistent_edges',
    'get_contradictory_pairs',
    'get_contradiction_summary',
    'count_diseases',
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
    return dict(edge_relations)


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


def get_unused_annotations(graph):
    """Gets the set of all annotations that are defined in a graph, but are never used.

    :param pybel.BELGraph graph: A BEL graph
    :return: A set of annotations
    :rtype: set[str] 
    """
    defined_annotations = set(graph.annotation_pattern) | set(graph.annotation_url) | set(graph.annotation_owl) | set(
        graph.annotation_list)
    return defined_annotations - get_annotations(graph)


def get_unused_list_annotation_values(graph):
    """Gets all of the unused values for list annotations
    
    :param pybel.BELGraph graph: A BEL graph
    :return: A dictionary of {str annotation: set of str values that aren't used}
    :rtype: dict[str, set[str]]
    """
    result = {}
    for annotation, values in graph.annotation_list.items():
        used_values = get_annotation_values(graph, annotation)
        if len(used_values) == len(values):  # all values have been used
            continue
        result[annotation] = set(values) - used_values
    return result


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


def _iter_pairs(graph):
    """Iterates over unique node-node pairs in the graph
    
    :param pybel.BELGraph graph: A BEL graph
    :rtype: iter
    """
    for u, v in set(graph.edges_iter()):
        yield u, v


def get_all_relations(graph, u, v):
    """Returns the set of all relations between a given pair of nodes
    
    :param pybel.BELGraph graph: A BEL graph
    :param tuple u: The source BEL node
    :param tuple v: The target BEL node
    :rtype: set
    """
    return {d[RELATION] for d in graph.edge[u][v].values()}


def pair_is_consistent(graph, u, v):
    """Returns if the edges between the given nodes are constitient, meaning they all have the same relation

    :param pybel.BELGraph graph: A BEL graph
    :param tuple u: The source BEL node
    :param tuple v: The target BEL node
    :return: Do the edges between these nodes all have the same relation
    :rtype: bool
    """
    relations = get_all_relations(graph, u, v)
    return 1 == len(relations)


def _pair_has_contradiction_helper(relations):
    has_increases = any(relation in CAUSAL_INCREASE_RELATIONS for relation in relations)
    has_decreases = any(relation in CAUSAL_DECREASE_RELATIONS for relation in relations)
    has_cnc = any(relation == CAUSES_NO_CHANGE for relation in relations)
    return 1 < sum([has_cnc, has_decreases, has_increases])


def pair_has_contradiction(graph, u, v):
    """Checks if a pair of nodes has any contradictions in their causal relationships.
    
    :param pybel.BELGraph graph: A BEL graph
    :param tuple u: The source BEL node
    :param tuple v: The target BEL node
    :return: Do the edges between these nodes have a contradiction?
    :rtype: bool
    """
    relations = get_all_relations(graph, u, v)
    return _pair_has_contradiction_helper(relations)


def get_contradictory_pairs(graph):
    """Iterates over contradictory node pairs in the graph based on their causal relationships
    
    :param graph: 
    :return: An iterator over (source, target) node pairs that have contradictory causal edges
    :rtype: iter
    """
    for u, v in _iter_pairs(graph):
        if pair_has_contradiction(graph, u, v):
            yield u, v


def get_contradiction_summary(graph):
    for u, v in _iter_pairs(graph):
        relations = get_all_relations(graph, u, v)
        if _pair_has_contradiction_helper(relations):
            yield u, v, relations


def get_consistent_edges(graph):
    """Returns an iterator over consistent edges

    :param pybel.BELGraph graph: A BEL graph
    :return: An iterator over (source, target) node pairs corresponding to edges with many inconsistent relations
    :rtype: iter
    """
    for u, v in _iter_pairs(graph):
        if pair_is_consistent(graph, u, v):
            yield u, v


def get_inconsistent_edges(graph):
    """Returns an iterator over inconsistent edges

    :param pybel.BELGraph graph: A BEL graph
    :return: An iterator over (source, target) node pairs corresponding to edges with many inconsistent relations
    :rtype: iter
    """
    for u, v in _iter_pairs(graph):
        if not pair_is_consistent(graph, u, v):
            yield u, v


def _disease_iterator(graph):
    """Iterates over the diseases encountered in edges
    
    :param pybel.BELGraph graph: A BEL graph
    :rtype: iter
    """
    for u, v in _iter_pairs(graph):
        if graph.node[u][FUNCTION] == PATHOLOGY:
            yield u
        if graph.node[v][FUNCTION] == PATHOLOGY:
            yield v


def count_diseases(graph):
    """Returns a counter of all of the mentions of diseases in a graph

    :param pybel.BELGraph graph: A BEL graph
    :rtype: Counter
    """
    return Counter(_disease_iterator(graph))
