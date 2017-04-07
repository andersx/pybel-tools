# -*- coding: utf-8 -*-

import logging
import os

from pybel import BELGraph, to_pickle
from pybel.constants import ANNOTATIONS, METADATA_NAME, GRAPH_METADATA
from .paths import get_nodes_in_shortest_paths, get_nodes_in_dijkstra_paths
from ..filters.edge_filters import filter_edges, build_citation_inclusion_filter, build_author_inclusion_filter, \
    keep_causal_edges, build_annotation_value_filter, build_annotation_dict_filter
from ..filters.node_filters import filter_nodes
from ..mutation.expansion import expand_node_neighborhood, expand_all_node_neighborhoods
from ..mutation.merge import left_merge
from ..summary.edge_summary import get_annotation_values
from ..utils import check_has_annotation, graph_edge_data_iter

log = logging.getLogger(__name__)

__all__ = [
    'get_subgraph_by_induction',
    'get_subgraph_by_edge_filter',
    'get_subgraph_by_node_filter',
    'get_subgraph_by_neighborhood',
    'get_subgraph_by_shortest_paths',
    'get_subgraph_by_annotation_value',
    'get_subgraph_by_data',
    'get_subgraph_by_pubmed',
    'get_subgraph_by_authors',
    'get_subgraph_by_provenance',
    'get_subgraph_by_provenance_helper',
    'get_causal_subgraph',
    'get_subgraph',
    'get_subgraphs_by_annotation',
    'subgraphs_to_pickles',
]

SEED_TYPE_INDUCTION = 'induction'
SEED_TYPE_NEIGHBORS = 'neighbors'
SEED_TYPE_PATHS = 'shortest_paths'
SEED_TYPE_PROVENANCE = 'provenance'

SEED_TYPES = {
    SEED_TYPE_INDUCTION,
    SEED_TYPE_NEIGHBORS,
    SEED_TYPE_PATHS,
    SEED_TYPE_PROVENANCE,
}

def get_subgraph_by_induction(graph, nodes):
    """Induces a graph on the given nodes

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param nodes: A list of nodes in the graph
    :type nodes: iter
    :return: An induced BEL subgraph
    :rtype: pybel.BELGraph
    """
    return graph.subgraph(nodes)


def get_subgraph_by_node_filter(graph, node_filters):
    """Induces a graph on the nodes that pass all filters

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param node_filters: A node filter (graph, node) -> bool or list of node filters (graph, node) -> bool
    :type node_filters: list or lambda
    :return: An induced BEL subgraph
    :rtype: pybel.BELGraph
    """
    return get_subgraph_by_induction(graph, filter_nodes(graph, node_filters))


def get_subgraph_by_neighborhood(graph, nodes):
    """Gets a BEL graph around the neighborhoods of the given nodes

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param nodes: An iterable of BEL nodes
    :type nodes: iter
    :return: A BEL graph induced around the neighborhoods of the given nodes
    :rtype: pybel.BELGraph
    """
    bg = BELGraph()

    node_set = set(nodes)

    for node in node_set:
        if node not in graph:
            raise ValueError('{} not in graph'.format(node))

    for u, v, k, d in graph.in_edges_iter(nodes, keys=True, data=True):
        bg.add_edge(u, v, key=k, attr_dict=d)

    for u, v, k, d in graph.out_edges_iter(nodes, keys=True, data=True):
        bg.add_edge(u, v, key=k, attr_dict=d)

    for node in bg.nodes_iter():
        bg.node[node].update(graph.node[node])

    return bg


def get_subgraph_by_shortest_paths(graph, nodes, cutoff=None, weight=None):
    """Induces a subgraph over the nodes in the pairwise shortest paths between all of the nodes in the given list

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param nodes: A set of nodes over which to calculate shortest paths
    :type nodes: set
    :param cutoff:  Depth to stop the shortest path search. Only paths of length <= cutoff are returned.
    :type cutoff: int
    :param weight: Edge data key corresponding to the edge weight. If None, performs unweighted search
    :type weight: str
    :return: A BEL graph induced over the nodes appearing in the shortest paths between the given nodes
    :rtype: pybel.BELGraph
    """
    if weight is None:
        return graph.subgraph(get_nodes_in_shortest_paths(graph, nodes, cutoff=cutoff))
    else:
        return graph.subgraph(get_nodes_in_dijkstra_paths(graph, nodes, cutoff=cutoff, weight=weight))


def get_subgraph_by_edge_filter(graph, edge_filters):
    """Induces a subgraph on all edges that pass the given filters
    
    :param graph: A BEL graph
    :type graph: pybel.BELGraph 
    :param edge_filters: A predicate or list of predicates (graph, node, node, key, data) -> bool
    :type edge_filters: list or tuple or lambda
    :return: A BEL subgraph induced over the edges passing the given filters
    :rtype: pybel.BELGraph
    """
    result = BELGraph()

    for u, v, k, d in filter_edges(graph, edge_filters):
        result.add_edge(u, v, key=k, attr_dict=d)

    for node in result.nodes_iter():
        result.node[node].update(graph.node[node])

    return result


def get_subgraph_by_annotation_value(graph, value, annotation='Subgraph'):
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
    g = get_subgraph_by_edge_filter(graph, build_annotation_value_filter(annotation, value))
    g.graph[GRAPH_METADATA][METADATA_NAME] = '{} - ({}: {})'.format(graph.name, annotation, value)
    return g


def get_subgraph_by_data(graph, annotations):
    """
    
    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param annotations: Annotation filters (match all with :func:`pybel.utils.subdict_matches`)
    :type annotations: dict
    :return: A subgraph of the original BEL graph
    :rtype: pybel.BELGraph
    """
    return get_subgraph_by_edge_filter(graph, build_annotation_dict_filter(annotations))


# TODO this is currently O(M^2) and can be easily done in O(M)
def get_subgraphs_by_annotation(graph, annotation='Subgraph'):
    """Builds a new subgraph induced over all edges for each value in the given annotation.

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param annotation: The annotation to group by
    :type annotation: str
    :return: A dictionary of {str value: BELGraph subgraph}
    :rtype: dict
    """
    values = get_annotation_values(graph, annotation)
    return {value: get_subgraph_by_annotation_value(graph, value, annotation=annotation) for value in values}


def get_causal_subgraph(graph):
    """Builds a new subgraph induced over all edges that are causal

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :return: A subgraph of the original BEL graph
    :rtype: pybel.BELGraph
    """
    result = get_subgraph_by_edge_filter(graph, keep_causal_edges)
    result.graph[GRAPH_METADATA][METADATA_NAME] = '{} - Induced Causal Subgraph'.format(graph.name)
    return result


def get_subgraph(graph, seed_method=None, seed_data=None, expand_nodes=None, remove_nodes=None, **annotations):
    """Runs pipeline query on graph with multiple subgraph filters and expanders

    Order of operations:
    1. Seeding by given function name and data
    2. Filter by annotations
    3. Add nodes
    4. Remove nodes

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param seed_method: The method to use.
    :type seed_method: str
    :param seed_data: The variable to pass as the arguments to the get_subgraph_by_* function
    :type seed_data: ???
    :param expand_nodes: Add the neighborhoods around all of these nodes
    :type expand_nodes: list
    :param remove_nodes: Remove these nodes and all of their in/out edges
    :type remove_nodes: list
    :param annotations: Annotation filters (match all with :func:`pybel.utils.subdict_matches`)
    :type annotations: dict
    :return: A BEL Graph
    :rtype: pybel.BELGraph
    """

    if seed_method == SEED_TYPE_INDUCTION:
        seed_graph = get_subgraph_by_induction(graph, seed_data)
    elif seed_method == SEED_TYPE_PATHS:
        seed_graph = get_subgraph_by_shortest_paths(graph, seed_data)
    elif seed_method == SEED_TYPE_NEIGHBORS:
        seed_graph = get_subgraph_by_neighborhood(graph, seed_data)
    elif seed_method == SEED_TYPE_PROVENANCE:
        seed_graph = get_subgraph_by_provenance(graph, seed_data)
    else:  # Otherwise, don't seed a subgraph
        seed_graph = graph

    # Filter by the given annotations
    subgraph = get_subgraph_by_data(seed_graph, {ANNOTATIONS: annotations})

    # Expand around the given nodes
    if expand_nodes:
        for node in expand_nodes:
            expand_node_neighborhood(graph, subgraph, node)

    # Delete the given nodes
    if remove_nodes:
        for node in remove_nodes:
            if node not in subgraph:
                log.warning('%s is not in graph %s', node, graph.name)
                continue
            subgraph.remove_node(node)

    return subgraph


def get_subgraph_by_pubmed(graph, pmids):
    """Induces a subgraph over the edges retrieved from the given PubMed identifier(s)"""
    return get_subgraph_by_edge_filter(graph, build_citation_inclusion_filter(pmids))


def get_subgraph_by_authors(graph, authors):
    """Induces a subgraph over the edges retrieved publications by the given author(s)"""
    return get_subgraph_by_edge_filter(graph, build_author_inclusion_filter(authors))


def subgraphs_to_pickles(graph, directory, annotation='Subgraph'):
    """Groups the given graph into subgraphs by the given annotation with :func:`get_subgraph_by_annotation` and
    outputs them as gpickle files to the given directory with :func:`pybel.to_pickle`

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param directory: A directory to output the pickles
    :type directory: str
    :param annotation: An annotation to split by. Suggestion: ``Subgraph``
    :type annotation: str
    """
    vs = {d[ANNOTATIONS][annotation] for d in graph_edge_data_iter(graph) if check_has_annotation(d, annotation)}

    for value in vs:
        sg = get_subgraph_by_annotation_value(graph, annotation, value)
        sg.document.update(graph.document)

        file_name = '{}_{}.gpickle'.format(annotation, value.replace(' ', '_'))
        path = os.path.join(directory, file_name)
        to_pickle(sg, path)


def get_subgraph_by_provenance(graph, kwargs):
    """Thin wrapper around :func:`get_subgraph_by_provenance_helper` by splatting keyword arguments"""
    return get_subgraph_by_provenance_helper(graph, **kwargs)


def get_subgraph_by_provenance_helper(graph, pmids=None, authors=None, expand_neighborhoods=True):
    """Gets all edges of given provenance and expands around their nodes' neighborhoods
    
    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param pmids: A PubMed identifier or list of PubMed identifiers
    :type pmids: str or list[str]
    :param authors: An author or list of authors
    :type authors: str or list[str]
    :param expand_neighborhoods: Should the neighborhoods around all nodes be expanded? Defaults to ``True``
    :type expand_neighborhoods: bool
    :return: An induced graph
    :rtype: pybel.BELGraph
    """
    if not pmids and not authors:
        raise ValueError('No citations nor authors given')

    result = BELGraph()

    if pmids:
        left_merge(result, get_subgraph_by_pubmed(graph, pmids))

    if authors:
        left_merge(result, get_subgraph_by_authors(graph, authors))

    if expand_neighborhoods:
        expand_all_node_neighborhoods(graph, result)

    return result
