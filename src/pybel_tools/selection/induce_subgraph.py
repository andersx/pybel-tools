# -*- coding: utf-8 -*-

import logging
import os

from pybel import BELGraph, to_pickle
from pybel.constants import ANNOTATIONS, RELATION, CAUSAL_RELATIONS, METADATA_NAME
from .paths import get_nodes_in_shortest_paths, get_nodes_in_dijkstra_paths
from ..filters.node_filters import filter_nodes
from ..mutation.expansion import expand_node_neighborhood
from ..utils import check_has_annotation

log = logging.getLogger(__name__)

__all__ = [
    'get_subgraph_by_node_filter',
    'get_subgraph_by_shortest_paths',
    'get_subgraph_by_annotation',
    'get_causal_subgraph',
    'filter_graph',
    'subgraphs_to_pickles',
]


def get_subgraph_by_node_filter(graph, *filters):
    """Induces a graph on the nodes that pass all filters

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param filters: a list of (graph, node) -> bool
    :return: An induced BEL subgraph
    :rtype: pybel.BELGraph
    """
    return graph.subgraph(filter_nodes(graph, *filters))


def get_subgraph_by_shortest_paths(graph, nodes, cutoff=None, weight=None):
    """Induces a subgraph over the nodes in the pairwise shortest paths between all of the nodes in the given list

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param nodes: A set of nodes over which to calculate shortest paths
    :type nodes: set
    :param cutoff:  Depth to stop the shortest path search. Only paths of length <= cutoff are returned.
    :type cutoff: int
    :param weight: Edge data key corresponding to the edge weight. If None, performs unwighted search
    :type weight: str
    :return: A BEL graph induced over the nodes appearing in the shortest paths between the given nodes
    :rtype: pybel.BELGraph
    """
    if weight is None:
        return graph.subgraph(get_nodes_in_shortest_paths(graph, nodes, cutoff=cutoff))
    else:
        return graph.subgraph(get_nodes_in_dijkstra_paths(graph, nodes, cutoff=cutoff, weight=weight))


def get_subgraph_by_annotation(graph, value, annotation='Subgraph'):
    """Builds a new subgraph induced over all edges whose annotations match the given key and value

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param value: The value for the annotation
    :type value: str
    :param annotation: The annotation to group by
    :type annotation: str
    :return: A subgraph of the original BEL graph
    :rtype: pybel.BELGraph
    """
    bg = BELGraph()
    bg.name = '{} - {} - {}'.format(graph.document[METADATA_NAME], annotation, value)

    for u, v, key, attr_dict in graph.edges_iter(keys=True, data=True):
        if not check_has_annotation(attr_dict, annotation):
            continue

        if attr_dict[ANNOTATIONS][annotation] == value:
            bg.add_edge(u, v, key=key, attr_dict=attr_dict)

    for node in bg.nodes_iter():
        bg.node[node].update(graph.node[node])

    return bg


def get_causal_subgraph(graph):
    """Builds a new subgraph induced over all edges that are causal

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :return: A subgraph of the original BEL graph
    :rtype: pybel.BELGraph
    """
    bg = BELGraph()

    for u, v, key, attr_dict in graph.edges_iter(keys=True, data=True):
        if attr_dict[RELATION] in CAUSAL_RELATIONS:
            bg.add_edge(u, v, key=key, attr_dict=attr_dict)

    for node in bg.nodes_iter():
        bg.node[node].update(graph.node[node])

    return bg


def filter_graph(graph, expand_nodes=None, remove_nodes=None, **annotations):
    """Queries graph's edges with multiple filters

    Order of operations:
    1. Match by annotations
    2. Add nodes
    3. Remove nodes

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param expand_nodes: Add the neighborhoods around all of these nodes
    :type expand_nodes: list
    :param remove_nodes: Remove these nodes and all of their in/out edges
    :type remove_nodes: list
    :param annotations: Annotation filters (match all with :func:`pybel.utils.subdict_matches`)
    :type annotations: dict
    :return: A BEL Graph
    :rtype: pybel.BELGraph
    """

    expand_nodes = [] if expand_nodes is None else expand_nodes
    remove_nodes = [] if remove_nodes is None else remove_nodes

    result_graph = BELGraph()

    for u, v, k, d in graph.edges_iter(keys=True, data=True, **{ANNOTATIONS: annotations}):
        result_graph.add_edge(u, v, key=k, attr_dict=d)

    for node in result_graph.nodes_iter():
        result_graph.node[node] = graph.node[node]

    for node in expand_nodes:
        expand_node_neighborhood(result_graph, graph, node)

    for node in remove_nodes:
        if node not in result_graph:
            log.warning('%s is not in graph %s', node, graph.name)
            continue

        result_graph.remove_node(node)

    return result_graph


def subgraphs_to_pickles(graph, directory, annotation='Subgraph'):
    """Groups the given graph into subgraphs by the given annotation with :func:`get_subgraph_by_annotation` and
    outputs them as gpickle files to the given directory with :func:`pybel.to_pickle`

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param directory: A directory to output the pickles
    :type directory: str
    :param annotation: An annotation to split by. Suggestion: 'Subgraph'
    :type annotation: str
    """

    vs = {d[ANNOTATIONS][annotation] for _, _, d in graph.edges_iter(data=True) if check_has_annotation(d, annotation)}

    for value in vs:
        sg = get_subgraph_by_annotation(graph, annotation, value)
        sg.document.update(graph.document)

        file_name = '{}_{}.gpickle'.format(annotation, value.replace(' ', '_'))
        path = os.path.join(directory, file_name)
        to_pickle(sg, path)
