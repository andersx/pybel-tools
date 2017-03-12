"""

This module contains functions that provide summaries of the edges in a graph

"""

import itertools as itt
from collections import Counter, defaultdict

from pybel.constants import RELATION, ANNOTATIONS
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
    'count_annotation_values_filtered'
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
    """Counts in how many edges each annotation appears in a graph

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param annotation: An annotation to count
    :type annotation: str
    :return: A Counter from {annotation value: frequency}
    :rtype: Counter
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
