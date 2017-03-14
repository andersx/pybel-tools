# -*- coding: utf-8 -*-

from collections import defaultdict

from pybel.constants import ANNOTATIONS
from ..filters.node_filters import keep_node_permissive
from ..utils import check_has_annotation

__all__ = [
    'group_nodes_by_annotation',
    'average_node_annotation',
    'group_nodes_by_annotation_filtered'
]


def group_nodes_by_annotation(graph, annotation='Subgraph'):
    """Groups the nodes occurring in edges by the given annotation

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param annotation: An annotation to use to group edges
    :type annotation: str
    :return: dict of sets of BELGraph nodes
    :rtype: dict
    """

    result = defaultdict(set)

    for u, v, d in graph.edges_iter(data=True):
        if not check_has_annotation(d, annotation):
            continue

        result[d[ANNOTATIONS][annotation]].add(u)
        result[d[ANNOTATIONS][annotation]].add(v)

    return result


def average_node_annotation(graph, key, annotation='Subgraph', aggregator=None):
    """Groups graph into subgraphs and assigns each subgraph a score based on the average of all nodes values
    for the given node key

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param key: The key in the node data dictionary representing the experimental data
    :type key: str
    :param annotation: A BEL annotation to use to group nodes
    :type annotation: str
    :param aggregator: A function from list of values -> aggregate value. Defaults to taking the average of a list of
                       floats.
    :type aggregator: lambda
    """

    if aggregator is None:
        aggregator = lambda x: sum(x) / len(x)

    result = {}
    grouping = group_nodes_by_annotation(graph, annotation)
    for subgraph, nodes in grouping.items():
        values = [graph.node[node][key] for node in nodes if key in graph.node[node]]
        result[subgraph] = aggregator(values)
    return result


def group_nodes_by_annotation_filtered(graph, node_filter=None, annotation='Subgraph'):
    """Groups the nodes occurring in edges by the given annotation, with a node filter applied

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param node_filter: A predicate (graph, node) -> bool for passing nodes
    :param annotation: The annotation to use for grouping
    :return: A dictionary of {annotation value: set of nodes}
    :rtype: dict
    """
    if node_filter is None:
        node_filter = keep_node_permissive

    return {k: {n for n in v if node_filter(graph, n)} for k, v in group_nodes_by_annotation(graph, annotation).items()}
