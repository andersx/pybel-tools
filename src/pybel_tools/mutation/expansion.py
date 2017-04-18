# -*- coding: utf-8 -*-

import itertools as itt
import logging
from collections import Counter, defaultdict

from pybel import BELGraph
from pybel.constants import *
from .merge import left_merge
from .utils import ensure_node_from_universe
from .. import pipeline
from ..filters.edge_filters import keep_edge_permissive, concatenate_edge_filters, edge_is_causal
from ..filters.node_filters import keep_node_permissive, concatenate_node_filters
from ..selection.utils import get_nodes_by_function
from ..summary.edge_summary import count_annotation_values
from ..utils import check_has_annotation, safe_add_edge

__all__ = [
    'get_upstream_causal_subgraph',
    'get_peripheral_successor_edges',
    'get_peripheral_predecessor_edges',
    'count_sources',
    'count_targets',
    'count_possible_successors',
    'count_possible_predecessors',
    'get_subgraph_edges',
    'get_subgraph_peripheral_nodes',
    'expand_periphery',
    'expand_node_neighborhood',
    'expand_all_node_neighborhoods',
    'expand_upstream_causal_subgraph',
    'enrich_grouping',
    'enrich_complexes',
    'enrich_composites',
    'enrich_reactions',
    'enrich_variants',
    'enrich_unqualified',
    'expand_internal',
    'expand_internal_causal',
]

log = logging.getLogger(__name__)


@pipeline.uni_mutator
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


def get_peripheral_successor_edges(graph, subgraph):
    """Gets the set of possible successor edges peripheral to the subgraph. The source nodes in this iterable are
    all inside the subgraph, while the targets are outside.

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


def get_peripheral_predecessor_edges(graph, subgraph):
    """Gets the set of possible predecessor edges peripheral to the subgraph. The target nodes in this iterable
    are all inside the subgraph, while the sources are outside.

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
    """Counts the source nodes in an edge iterator with keys and data

    :param edge_iter: An iterable on possible predecessor edges (4-tuples of node, node, key, data)
    """
    return Counter(u for u, _, _, _ in edge_iter)


def count_targets(edge_iter):
    """Counts the target nodes in an edge iterator with keys and data

    :param edge_iter: An iterable on possible predecessor edges (4-tuples of node, node, key, data)
    """
    return Counter(v for _, v, _, _ in edge_iter)


def count_possible_successors(graph, subgraph):
    return count_targets(get_peripheral_successor_edges(graph, subgraph))


def count_possible_predecessors(graph, subgraph):
    return count_sources(get_peripheral_predecessor_edges(graph, subgraph))


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


def get_subgraph_peripheral_nodes(graph, subgraph, node_filters=None, edge_filters=None):
    """Gets a summary dictionary of all peripheral nodes to a given subgraph

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param subgraph: A set of nodes
    :type subgraph: iter
    :param node_filters: Optional. A list of node filter predicates with the interface (graph, node) -> bool. See
                         :mod:`pybel_tools.filters.node_filters` for more information
    :type node_filters: lambda
    :param edge_filters: Optional. A list of edge filter predicates with the interface (graph, node, node, key, data)
                          -> bool. See :mod:`pybel_tools.filters.edge_filters` for more information
    :type edge_filters: lambda
    :return: A dictionary of {external node: {'successor': {internal node: list of (key, dict)},
                                            'predecessor': {internal node: list of (key, dict)}}}
    :rtype: dict

    For example, it might be useful to quantify the number of predecessors and successors

    >>> import pybel_tools as pbt
    >>> sgn = 'Blood vessel dilation subgraph'
    >>> sg = pbt.selection.get_subgraph_by_annotation_value(graph, value=sgn, annotation='Subgraph')
    >>> p = pbt.mutation.get_subgraph_peripheral_nodes(graph, sg, node_filters=pbt.filters.exclude_pathology_filter)
    >>> for node in sorted(p, key=lambda node: len(set(p[node]['successor']) | set(p[node]['predecessor'])), reverse=True):
    >>>     if 1 == len(p[sgn][node]['successor']) or 1 == len(p[sgn][node]['predecessor']):
    >>>         continue
    >>>     print(node,
    >>>           len(p[node]['successor']),
    >>>           len(p[node]['predecessor']),
    >>>           len(set(p[node]['successor']) | set(p[node]['predecessor'])))
    """
    node_filter = concatenate_node_filters(node_filters)
    edge_filter = concatenate_edge_filters(edge_filters)

    result = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    for u, v, k, d in get_peripheral_successor_edges(graph, subgraph):
        if not node_filter(graph, v) or not node_filter(graph, u) or not edge_filter(graph, u, v, k, d):
            continue
        result[v]['predecessor'][u].append((k, d))

    for u, v, k, d in get_peripheral_predecessor_edges(graph, subgraph):
        if not node_filter(graph, v) or not node_filter(graph, u) or not edge_filter(graph, u, v, k, d):
            continue
        result[u]['successor'][v].append((k, d))

    return result


def expand_periphery(graph, subgraph, node_filters=None, edge_filters=None, threshold=2):
    """Iterates over all possible edges, peripheral to a given subgraph, that could be added from the given graph.
    Edges could be added if they go to nodes that are involved in relationships that occur with more than the
    threshold (default 2) number of nodes in the subgraph.

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param subgraph: A set of nodes
    :type subgraph: iter
    :param node_filters: Optional. A list of node filter predicates with the interface (graph, node) -> bool. See
                         :mod:`pybel_tools.filters.node_filters` for more information
    :type node_filters: lambda
    :param edge_filters: Optional. A list of edge filter predicates with the interface (graph, node, node, key, data)
                          -> bool. See :mod:`pybel_tools.filters.edge_filters` for more information
    :type edge_filters: lambda
    :param threshold: Minimum frequency of betweenness occurrence to add a gap node

    A reasonable edge filter to use is :func:`pybel_tools.filters.keep_causal_edges` because this function can allow
    for huge expansions if there happen to be hub nodes.
    """
    nd = get_subgraph_peripheral_nodes(graph, subgraph, node_filters=node_filters, edge_filters=edge_filters)

    for node, dd in nd.items():
        pred_d = dd['predecessor']
        succ_d = dd['successor']

        in_subgraph_connections = set(pred_d) | set(succ_d)

        if threshold > len(in_subgraph_connections):
            continue

        subgraph.add_node(node, attr_dict=graph.node[node])

        for u, edges in pred_d.items():
            for k, d in edges:
                safe_add_edge(subgraph, u, node, k, d)

        for v, edges in succ_d.items():
            for k, d in edges:
                safe_add_edge(subgraph, node, v, k, d)


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


@pipeline.uni_in_place_mutator
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


@pipeline.uni_in_place_mutator
def enrich_complexes(graph, subgraph):
    """Adds all of the members of the complexes in the subgraph that are in the original graph with appropriate
    :data:`pybel.constants.HAS_COMPONENT` relationships, in place.

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param subgraph: A BEL graph's subgraph
    :type subgraph: pybel.BELGraph
    """
    enrich_grouping(graph, subgraph, COMPLEX, HAS_COMPONENT)


@pipeline.uni_in_place_mutator
def enrich_composites(graph, subgraph):
    """Adds all of the members of the composite abundances in the subgraph that are in the original graph with
    appropriate :data:`pybel.constants.HAS_COMPONENT` relationships, in place.

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param subgraph: A BEL graph's subgraph
    :type subgraph: pybel.BELGraph
    """
    enrich_grouping(graph, subgraph, COMPOSITE, HAS_COMPONENT)


@pipeline.uni_in_place_mutator
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


@pipeline.uni_in_place_mutator
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


@pipeline.uni_in_place_mutator
def enrich_variants(graph, subgraph):
    """Adds the reference nodes for all variants of genes, RNAs, miRNAs, and proteins

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param subgraph: A BEL graph's subgraph
    :type subgraph: pybel.BELGraph

    Equivalent to:

    >>> from pybel.constants import PROTEIN, RNA, MIRNA, GENE
    >>> enrich_variants_helper(graph, subgraph, PROTEIN)
    >>> enrich_variants_helper(graph, subgraph, RNA)
    >>> enrich_variants_helper(graph, subgraph, MIRNA)
    >>> enrich_variants_helper(graph, subgraph, GENE)

    .. seealso:: :func:`enrich_variants_helper`
    """
    enrich_variants_helper(graph, subgraph, PROTEIN)
    enrich_variants_helper(graph, subgraph, RNA)
    enrich_variants_helper(graph, subgraph, MIRNA)
    enrich_variants_helper(graph, subgraph, GENE)


@pipeline.uni_in_place_mutator
def enrich_unqualified(graph, subgraph):
    """Enriches the subgraph with the unqualified edges from the graph.

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param subgraph: A BEL graph's subgraph
    :type subgraph: pybel.BELGraph

    The reason you might want to do this is you induce a subgraph from the original graph based on an annotation filter,
    but the unqualified edges that don't have annotations that most likely connect elements within your graph are
    not included.

    .. seealso:: :func:`enrich_complexes`, :func:`enrich_composites`, :func:`enrich_reactions`, and :func:`enrich_variants`.

    Equivalent to:

    >>> enrich_complexes(graph, subgraph)
    >>> enrich_composites(graph, subgraph)
    >>> enrich_reactions(graph, subgraph)
    >>> enrich_variants(graph, subgraph)
    """
    enrich_complexes(graph, subgraph)
    enrich_composites(graph, subgraph)
    enrich_reactions(graph, subgraph)
    enrich_variants(graph, subgraph)


@pipeline.uni_in_place_mutator
def expand_internal(graph, subgraph, edge_filters=None):
    """Edges between entities in the subgraph that pass the given filters

    :param graph: The full graph
    :type graph: pybel.BELGraph
    :param subgraph: A subgraph to find the upstream information
    :type subgraph: pybel.BELGraph
    :param edge_filters: Optional list of edge filter functions (graph, node, node, key, data) -> bool
    :type edge_filters: list or lambda
    """
    edge_filter = concatenate_edge_filters(*edge_filters) if edge_filters else keep_edge_permissive

    for u, v in itt.product(subgraph.nodes_iter(), 2):
        if subgraph.has_edge(u, v) or not graph.has_edge(u, v):
            continue

        rs = defaultdict(list)
        for k, d in graph.edge[u][v].items():
            if not edge_filter(graph, u, v, k, d):
                continue

            rs[d[RELATION]].append(d)

        if 1 == len(rs):
            relation = list(rs)[0]
            for d in rs[relation]:
                subgraph.add_edge(u, v, attr_dict=d)
        else:
            log.debug('Multiple relationship types found between %s and %s', u, v)


@pipeline.uni_in_place_mutator
def expand_internal_causal(graph, subgraph):
    """Adds causal edges between entities in the subgraph. Is an extremely thin wrapper around :func:`expand_internal`.

    :param graph: The full graph
    :type graph: pybel.BELGraph
    :param subgraph: A subgraph to find the upstream information
    :type subgraph: pybel.BELGraph

    Equivalent to:

    >>> import pybel_tools as pbt
    >>> pbt.mutation.expand_internal(graph, subgraph, edge_filters=pbt.filters.edge_is_causal)
    """
    expand_internal(graph, subgraph, edge_filters=edge_is_causal)


@pipeline.uni_in_place_mutator
def expand_node_predecessors(universe, graph, node):
    """Expands around the predecessors of the given node in the result graph by looking at the universe graph,
    in place.
    
    :param universe: The graph containing the stuff to add
    :type universe: pybel.BELGraph
    :param graph: The graph to add stuff to
    :type graph: pybel.BELGraph
    :param node: A node tuples from the query graph
    :type node: tuple
    """
    ensure_node_from_universe(universe, graph, node)

    skip_successors = set()
    for successor in universe.successors_iter(node):
        if successor in graph:
            skip_successors.add(successor)
            continue
        graph.add_node(successor, attr_dict=universe.node[successor])

    for _, successor, k, d in universe.out_edges_iter(node, data=True, keys=True):
        if successor in skip_successors:
            continue
        safe_add_edge(graph, node, successor, k, d)


@pipeline.uni_in_place_mutator
def expand_node_successors(universe, graph, node):
    """Expands around the successors of the given node in the result graph by looking at the universe graph,
    in place.
    
    :param universe: The graph containing the stuff to add
    :type universe: pybel.BELGraph
    :param graph: The graph to add stuff to
    :type graph: pybel.BELGraph
    :param node: A node tuples from the query graph
    :type node: tuple
    """
    ensure_node_from_universe(universe, graph, node)

    skip_predecessors = set()
    for predecessor in universe.predecessors_iter(node):
        if predecessor in graph:
            skip_predecessors.add(predecessor)
            continue
        graph.add_node(predecessor, attr_dict=universe.node[predecessor])

    for predecessor, _, k, d in universe.in_edges_iter(node, data=True, keys=True):
        if predecessor in skip_predecessors:
            continue
        safe_add_edge(graph, predecessor, node, k, d)


@pipeline.uni_in_place_mutator
def expand_node_neighborhood(universe, graph, node):
    """Expands around the neighborhoods of the given node in the result graph by looking at the universe graph,
    in place.

    :param universe: The graph containing the stuff to add
    :type universe: pybel.BELGraph
    :param graph: The graph to add stuff to
    :type graph: pybel.BELGraph
    :param node: A node tuples from the query graph
    :type node: tuple
    """
    expand_node_predecessors(universe, graph, node)
    expand_node_successors(universe, graph, node)


@pipeline.uni_in_place_mutator
def expand_all_node_neighborhoods(universe, graph):
    """Expands the neighborhoods of all nodes in the given graph based on the universe graph.
    
    :param universe: The graph containing the stuff to add
    :type universe: pybel.BELGraph
    :param graph: The graph to add stuff to
    :type graph: pybel.BELGraph 
    """
    for node in graph.nodes():
        expand_node_neighborhood(universe, graph, node)


@pipeline.uni_in_place_mutator
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
