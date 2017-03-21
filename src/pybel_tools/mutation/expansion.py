# -*- coding: utf-8 -*-

import itertools as itt
import logging
from collections import Counter, defaultdict

from pybel import BELGraph
from pybel.constants import *
from .merge import left_merge
from ..filters.edge_filters import keep_edge_permissive, concatenate_edge_filters
from ..filters.node_filters import keep_node_permissive, concatenate_node_filters
from ..selection.utils import get_nodes_by_function
from ..summary.edge_summary import count_annotation_values
from ..utils import check_has_annotation

__all__ = [
    'get_upstream_causal_subgraph',
    'get_possible_successor_edges',
    'get_possible_predecessor_edges',
    'count_sources',
    'count_targets',
    'count_possible_successors',
    'count_possible_predecessors',
    'get_subgraph_edges',
    'get_subgraph_fill_edges',
    'fill_subgraph',
    'expand_node_neighborhood',
    'expand_upstream_causal_subgraph',
    'enrich_grouping',
    'enrich_complexes',
    'enrich_composites',
    'enrich_reactions',
    'enrich_unqualified',
    'expand_internal_causal'
]

log = logging.getLogger(__name__)


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


def get_possible_successor_edges(graph, subgraph):
    """Gets the set of possible successor edges peripheral to the subgraph

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param subgraph: A set of nodes
    :return: An iterable of possible successor edges (4-tuples of node, node, key, data)
    :rtype: iter
    """
    for u in subgraph.nodes_iter():
        for _, v, k, d in graph.out_edges_iter(u, keys=True, data=True):
            if v not in subgraph:
                yield u, v, k, d


def get_possible_predecessor_edges(graph, subgraph):
    """Gets the set of possible predecessor edges peripheral to the subgraph

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param subgraph: A set of nodes
    :return: An iterable on possible predecessor edges (4-tuples of node, node, key, data)
    :rtype: iter
    """
    for v in subgraph.nodes_iter():
        for u, _, k, d in graph.in_edges_iter(v, keys=True, data=True):
            if u not in subgraph:
                yield u, v, k, d


def count_sources(edge_iter):
    """Counts the source nodes in an edge iterator with keys and data"""
    return Counter(u for u, _, _, _ in edge_iter)


def count_targets(edge_iter):
    """Counts the target nodes in an edge iterator with keys and data"""
    return Counter(v for _, v, _, _ in edge_iter)


def count_possible_successors(graph, subgraph):
    return count_targets(get_possible_successor_edges(graph, subgraph))


def count_possible_predecessors(graph, subgraph):
    return count_sources(get_possible_predecessor_edges(graph, subgraph))


def get_subgraph_edges(graph, value, annotation='Subgraph', source_filter=None, target_filter=None):
    """Gets all edges from a given subgraph whose source and target nodes pass all of the given filters

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param value: The annotation value to search by
    :param annotation:  The annotation to search
    :param source_filter: Optional filter for source nodes (graph, node) -> bool
    :param target_filter: Optional filter for target nodes (graph, node) -> bool
    :return: An iterable of (source node, target node, key, data) for all edges that match the annotation/value and
             node filters
    :rtype: iter
    """
    if source_filter is None:
        source_filter = keep_node_permissive

    if target_filter is None:
        target_filter = keep_node_permissive

    for u, v, k, d in graph.edges_iter(keys=True, data=True):
        if not check_has_annotation(d, annotation):
            continue
        if d[ANNOTATIONS][annotation] == value and source_filter(graph, u) and target_filter(graph, v):
            yield u, v, k, d


def get_subgraph_fill_edges(graph, subgraph, node_filters=None, edge_filters=None, threshold=2):
    """Iterates over all possible edges, peripheral to a given subgraph, that could be added from the given graph.
    Edges could be added if they go to nodes that are involved in relationships that occur with more than the
    threshold (default 2) number of nodes in the subgraph.

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param subgraph: A set of nodes
    :type subgraph: iter
    :param node_filters: Optional. A list of node filter predicates with the interface (graph, node) -> bool. See
                         :code:`pybel_tools.filters.node_filters` for more information
    :type node_filter: lambda
    :param edge_filters: Optional. A list of edge filter predicates with the interface (graph, node, node, key, data)
                          -> bool. See :code:`pybel_tools.filters.edge_filters` for more information
    :type edge_filter: lambda
    :param threshold: Minimum frequency of betweenness occurrence to add a gap node
    :return: An iterable of (source node, target node, key, data) for all edges that could be added to the subgraph
    :rtype: iter
    """
    node_filter = concatenate_node_filters(node_filters) if node_filters else keep_node_permissive
    edge_filter = concatenate_edge_filters(edge_filters) if edge_filters else keep_edge_permissive

    possible_succ = list(get_possible_successor_edges(graph, subgraph))
    succ_counter = count_targets(possible_succ)

    possible_pred = list(get_possible_predecessor_edges(graph, subgraph))
    pred_counter = count_sources(possible_pred)

    gaps = set()
    for n, freq in (succ_counter + pred_counter).items():
        if threshold <= freq and node_filter(graph, n):
            gaps.add(n)

    for already_in_graph, new_node, k, d in possible_succ:
        if new_node in gaps and edge_filter(graph, already_in_graph, new_node, k, d):
            yield already_in_graph, new_node, k, d

    for new_node, already_in_graph, k, d in possible_pred:
        if new_node in gaps and edge_filter(graph, new_node, already_in_graph, k, d):
            yield new_node, already_in_graph, k, d


def fill_subgraph(graph, subgraph, node_filters=None, edge_filters=None, threshold=2):
    """Calculates what nodes can be added to the subgraph with :func:`get_subgraph_fill_edges` and adds them

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param subgraph: A BEL graph
    :type subgraph: pybel.BELGraph
    :param node_filters: Optional list of node filter functions (graph, node) -> bool
    :type node_filters: list
    :param edge_filters: Optional list of edge filter functions (graph, node, node, key, data) -> bool
    :type edge_filters: list
    :param threshold: Minimum frequency of betweenness occurrence to add a gap node
    :type threshold: int
    """
    for u, v, k, d in get_subgraph_fill_edges(graph, subgraph, node_filters, edge_filters, threshold):
        if u not in subgraph:
            subgraph.add_node(u, attr_dict=graph.node[u])
        if v not in subgraph:
            subgraph.add_node(v, attr_dict=graph.node[v])
        subgraph.add_edge(u, v, key=k, attr_dict=d)


# TODO implement
def infer_subgraph_expansion(graph, annotation='Subgraph'):
    """Infers the annotations for subgraphs on to edges

    1. Group subgraphs
    2. Build dictionary of {(u,v,k): {set of inferred subgraph names}}

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param annotation: The annotation to infer
    :type annotation: str
    """

    inferred_subgraphs = defaultdict(set)
    subgraph_counts = count_annotation_values(graph, annotation)
    raise NotImplementedError


def enrich_grouping(graph, subgraph, function, relation):
    """Adds all of the grouped elements. See :func:`enrich_complexes`, :func:`enrich_composites`, and
    :func:`enrich_reactions`

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param subgraph: A BEL graph's subgraph
    :type subgraph: pybel.BELGraph
    """
    nodes = list(get_nodes_by_function(subgraph, function))
    for u in nodes:
        for _, v, d in graph.out_edges_iter(u, data=True):
            if d[RELATION] != relation:
                continue

            if v not in subgraph:
                subgraph.add_node(v, attr_dict=graph.node[v])

            if v not in subgraph.edge[u] or unqualified_edge_code[relation] not in subgraph.edge[u][v]:
                subgraph.add_unqualified_edge(u, v, relation)


def enrich_complexes(graph, subgraph):
    """Adds all of the members of the complexes in the subgraph that are in the original graph with appropriate
    :data:`pybel.constants.HAS_COMPONENT` relationships, in place.

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param subgraph: A BEL graph's subgraph
    :type subgraph: pybel.BELGraph
    """
    enrich_grouping(graph, subgraph, COMPLEX, HAS_COMPONENT)


def enrich_composites(graph, subgraph):
    """Adds all of the members of the composite abundances in the subgraph that are in the original graph with
    appropriate :data:`pybel.constants.HAS_COMPONENT` relationships, in place.

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param subgraph: A BEL graph's subgraph
    :type subgraph: pybel.BELGraph
    """
    enrich_grouping(graph, subgraph, COMPOSITE, HAS_COMPONENT)


def enrich_reactions(graph, subgraph):
    """Adds all of the reactants and products of reactions in the subgraph that are in the original graph with
    appropriate :data:`pybel.constants.HAS_REACTANT` and :data:`pybel.constants.HAS_PRODUCT` relationships,
    respectively, in place.

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param subgraph: A BEL graph's subgraph
    :type subgraph: pybel.BELGraph
    """
    enrich_grouping(graph, subgraph, REACTION, HAS_REACTANT)
    enrich_grouping(graph, subgraph, REACTION, HAS_PRODUCT)


def enrich_variants_helper(graph, subgraph, function):
    """Adds the reference nodes for all variants of the given function

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param subgraph: A BEL graph's subgraph
    :type subgraph: pybel.BELGraph
    :param function: The BEL function to filter by
    :type function: str
    """
    nodes = list(get_nodes_by_function(subgraph, function))
    for v in nodes:
        for u, _, d in graph.in_edges_iter(v, data=True):
            if d[RELATION] != HAS_VARIANT:
                continue

            if u not in subgraph:
                subgraph.add_node(u, attr_dict=graph.node[u])

            if v not in subgraph.edge[u] or unqualified_edge_code[HAS_VARIANT] not in subgraph.edge[u][v]:
                subgraph.add_unqualified_edge(u, v, HAS_VARIANT)


def enrich_variants(graph, subgraph):
    """Adds the reference nodes for all variants of genes, RNAs, miRNAs, and proteins

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param subgraph: A BEL graph's subgraph
    :type subgraph: pybel.BELGraph
    """
    enrich_variants_helper(graph, subgraph, PROTEIN)
    enrich_variants_helper(graph, subgraph, RNA)
    enrich_variants_helper(graph, subgraph, MIRNA)
    enrich_variants_helper(graph, subgraph, GENE)


def enrich_unqualified(graph, subgraph):
    """Enriches the subgraph with the unqualified edges from the graph.

    The reason you might want to do this is you induce a subgraph from the original graph based on an annotation filter,
    but the unqualified edges that don't have annotations that most likely connect elements within your graph are
    not included.


    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param subgraph: A BEL graph's subgraph
    :type subgraph: pybel.BELGraph
    """
    enrich_complexes(graph, subgraph)
    enrich_composites(graph, subgraph)
    enrich_reactions(graph, subgraph)
    enrich_variants(graph, subgraph)


def expand_internal_causal(graph, subgraph):
    """Adds causal edges between entities in the subgraph.

    :param graph: The full graph
    :type graph: pybel.BELGraph
    :param subgraph: A subgraph to find the upstream information
    :type subgraph: pybel.BELGraph

    Future:

    :param target_filter: A predicate for target nodes (graph, node) -> bool. Could be used to not match nodes that
                          are the causal root for a tree that's being grown
    :type target_filter: lambda

    """
    for u, v in itt.product(subgraph.nodes_iter(), 2):
        if subgraph.has_edge(u, v) or not graph.has_edge(u, v):
            continue

        rs = defaultdict(list)
        for k, d in graph.edge[u][v].items():
            if d[RELATION] not in CAUSAL_RELATIONS:
                continue
            rs[d[RELATION]].append(d)

        if 1 == len(rs):
            relation = list(rs)[0]
            for d in rs[relation]:
                subgraph.add_edge(u, v, attr_dict=d)
        else:
            log.debug('Multiple relationship types found between %s and %s', u, v)


def expand_node_neighborhood(graph, subgraph, node):
    """Expands around the neighborhoods of the given nodes in the result graph by looking at the original_graph,
    in place.

    :param graph: The graph containing the stuff to add
    :type graph: pybel.BELGraph
    :param subgraph: The graph to add stuff to
    :type subgraph: pybel.BELGraph
    :param node: A node tuples from the query graph
    :type node: tuple
    """
    if node not in graph:
        raise ValueError('{} not in graph {}'.format(node, subgraph.name))

    if node not in subgraph:
        subgraph.add_node(node, attr_dict=graph.node[node])

    skip_predecessors = set()
    for predecessor in graph.predecessors_iter(node):
        if predecessor in subgraph:
            skip_predecessors.add(predecessor)
            continue
        subgraph.add_node(predecessor, attr_dict=graph.node[node])

    for predecessor, _, k, d in graph.in_edges_iter(node, data=True, keys=True):
        if predecessor in skip_predecessors:
            continue

        if k < 0:
            subgraph.add_edge(predecessor, node, key=k, attr_dict=d)
        else:
            subgraph.add_edge(predecessor, node, attr_dict=d)

    skip_successors = set()
    for successor in graph.successors_iter(node):
        if successor in subgraph:
            skip_successors.add(successor)
            continue
        subgraph.add_node(successor, attr_dict=graph.node[node])

    for _, successor, k, d in graph.out_edges_iter(node, data=True, keys=True):
        if successor in skip_successors:
            continue

        if k < 0:
            subgraph.add_edge(node, successor, key=k, attr_dict=d)
        else:
            subgraph.add_edge(node, successor, attr_dict=d)


def expand_upstream_causal_subgraph(graph, subgraph):
    """Adds the upstream causal relations to the given subgraph

    :param graph: The full graph
    :type graph: pybel.BELGraph
    :param subgraph: A subgraph to find the upstream information
    :type subgraph: pybel.BELGraph
    """
    for node in subgraph.nodes():
        upstream = get_upstream_causal_subgraph(graph, node)
        left_merge(subgraph, upstream)
