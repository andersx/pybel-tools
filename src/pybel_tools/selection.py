"""

This module contains functions to help select data from networks

"""
import logging
from collections import defaultdict
from itertools import combinations

from pybel import BELGraph
from pybel.constants import ANNOTATIONS, RELATION, CAUSAL_RELATIONS, FUNCTION, METADATA_NAME
from .filters.node_filters import filter_nodes, keep_node_permissive
from .utils import check_has_annotation

log = logging.getLogger(__name__)


def get_nodes_by_function(graph, function):
    """Get all nodes of a given type

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param function: The BEL function to filter by
    :type function: str
    :return: An iterable of all BEL nodes with the given function
    :rtype: iter
    """
    for node, data in graph.nodes_iter(data=True):
        if data[FUNCTION] == function:
            yield node


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


def get_subgraph_by_node_filter(graph, *filters):
    """Induces a graph on the nodes that pass all filters

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param filters: a list of (graph, node) -> bool
    :return: An induced BEL subgraph
    :rtype: pybel.BELGraph
    """
    return graph.subgraph(filter_nodes(graph, *filters))


def get_subgraph_by_annotation(graph, value, annotation='Subgraph'):
    """Builds a new subgraph induced over all edges whose annotations match the given key and value

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param value: The value for the annotation
    :type value: str
    :param annotation: An annotation
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


def get_upstream_causal_subgraph(graph, nbunch):
    """Induces a subgraph from all of the upstream causal entities of the nodes in the nbunch

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param nbunch: A BEL node or iterable of BEL nodes
    :type nbunch: tuple or list of tuples
    :return: A BEL Graph
    :rtype: pybel.BELGraph
    """
    bg = BELGraph()

    for u, v, k, d in graph.in_edges_iter(nbunch, keys=True, data=True):
        if d[RELATION] in CAUSAL_RELATIONS:
            bg.add_edge(u, v, key=k, attr_dict=d)

    for node in bg.nodes_iter():
        bg.node[node].update(graph.node[node])

    return bg


def get_triangles(graph, node):
    """Yields all triangles pointed by the given node

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param node: The source node
    :type node: tuple
    """
    for a, b in combinations(graph.edge[node], 2):
        if graph.edge[a][b]:
            yield a, b
        if graph.edge[b][a]:
            yield b, a


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


def expand_node_neighborhood(graph, query_graph, node):
    """Expands around the neighborhoods of the given nodes in the result graph by looking at the original_graph,
    in place.

    :param graph: The graph to add stuff to
    :type graph: pybel.BELGraph
    :param query_graph: The graph containing the stuff to add
    :type query_graph: pybel.BELGraph
    :param node: A node tuples from the query graph
    :type node: tuple
    """
    if node not in query_graph:
        raise ValueError('{} not in graph {}'.format(node, graph.name))

    if node not in graph:
        graph.add_node(node, attr_dict=query_graph.node[node])

    skip_predecessors = set()
    for predecessor in query_graph.predecessors_iter(node):
        if predecessor in graph:
            skip_predecessors.add(predecessor)
            continue
        graph.add_node(predecessor, attr_dict=query_graph.node[node])

    for predecessor, _, k, d in query_graph.in_edges_iter(node, data=True, keys=True):
        if predecessor in skip_predecessors:
            continue

        if k < 0:
            graph.add_edge(predecessor, node, key=k, attr_dict=d)
        else:
            graph.add_edge(predecessor, node, attr_dict=d)

    skip_successors = set()
    for successor in query_graph.successors_iter(node):
        if successor in graph:
            skip_successors.add(successor)
            continue
        graph.add_node(successor, attr_dict=query_graph.node[node])

    for _, successor, k, d in query_graph.out_edges_iter(node, data=True, keys=True):
        if successor in skip_successors:
            continue

        if k < 0:
            graph.add_edge(node, successor, key=k, attr_dict=d)
        else:
            graph.add_edge(node, successor, attr_dict=d)
