# -*- coding: utf-8 -*-

import itertools as itt
import logging

from pybel.constants import *
from .collapse import collapse_by_central_dogma, collapse_by_central_dogma_to_genes
from ..constants import INFERRED_INVERSE

__all__ = [
    'infer_central_dogma',
    'infer_missing_two_way_edges',
    'infer_missing_backwards_edge',
    'infer_missing_inverse_edge',
    'add_missing_unqualified_edges',
    'opening_by_central_dogma',
    'opening_by_central_dogma_to_genes',
]

log = logging.getLogger(__name__)


def _infer_converter_helper(node, data, new_function):
    new_tup = list(node)
    new_tup[0] = new_function
    new_tup = tuple(new_tup)
    new_dict = data.copy()
    new_dict[FUNCTION] = new_function
    return new_tup, new_dict


def infer_central_dogmatic_translations(graph):
    """For all Protein entities, adds the missing origin RNA and RNA-Protein translation edge

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    """
    for node, data in graph.nodes(data=True):
        if data[FUNCTION] == PROTEIN and NAMESPACE in data and VARIANTS not in data:
            rna_node, rna_attr_dict = _infer_converter_helper(node, data, RNA)
            graph.add_node(rna_node, attr_dict=rna_attr_dict)
            graph.add_unqualified_edge(rna_node, node, TRANSLATED_TO)


def infer_central_dogmatic_transcriptions(graph):
    """For all RNA entities, adds the missing origin Gene and Gene-RNA transcription edge

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    """
    for node, data in graph.nodes(data=True):
        if data[FUNCTION] in {MIRNA, RNA} and NAMESPACE in data and VARIANTS not in data:
            gene_node, gene_attr_dict = _infer_converter_helper(node, data, GENE)
            graph.add_node(gene_node, attr_dict=gene_attr_dict)
            graph.add_unqualified_edge(gene_node, node, TRANSCRIBED_TO)


def infer_central_dogma(graph):
    """Adds all RNA-Protein translations then all Gene-RNA transcriptions by applying
    :code:`infer_central_dogmatic_translations` then :code:`infer_central_dogmatic_transcriptions`

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    """
    infer_central_dogmatic_translations(graph)
    infer_central_dogmatic_transcriptions(graph)


def infer_missing_two_way_edges(graph):
    """If a two way edge exists, and the opposite direction doesn't exist, add it to the graph

    Use: two way edges from BEL definition and/or axiomatic inverses of membership relations

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    """
    for u, v, k, d in graph.edges_iter(data=True, keys=True):
        if d[RELATION] in TWO_WAY_RELATIONS:
            infer_missing_backwards_edge(graph, u, v, k, d)


def infer_missing_inverse_edge(graph, relations):
    """Adds inferred edges based on pre-defined axioms

    :param graph: a BEL network
    :type graph: pybel.BELGraph
    :param relations: single or iterable of relation names to add their inverse inferred edges
    :type relations: str or list
    """

    if isinstance(relations, str):
        return infer_missing_inverse_edge(graph, [relations])

    for relation in relations:
        for u, v in graph.edges_iter(**{RELATION: relation}):
            graph.add_edge(v, u, key=unqualified_edge_code[relation], **{RELATION: INFERRED_INVERSE[relation]})


def infer_missing_backwards_edge(graph, u, v, k, d):
    """Adds the same edge, but in the opposite direction if not already present

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param u: A BEL node
    :type u: tuple
    :param v: A BEL node
    :type u: tuple
    :param k: The edge key
    :type k: int
    :param d: The data dictionary from the connection between (u, v)
    :type d: dict
    """

    for attr_dict in graph.edge[v][u].values():
        if attr_dict == d:
            return

    if k < 0:
        graph.add_edge(v, u, key=k, attr_dict=d)
    else:
        graph.add_edge(v, u, attr_dict=d)


def add_missing_unqualified_edges(subgraph, graph):
    """Adds the missing unqualified edges between entities in the subgraph that are contained within the full graph

    :param subgraph: The query BEL subgraph
    :type subgraph: pybel.BELGraph
    :param graph: The full BEL graph
    :type graph: pybel.BELGraph
    """
    for u, v in itt.combinations(subgraph.nodes_iter(), 2):
        if not graph.has_edge(u, v):
            continue

        for k in graph.edge[u][v]:
            if k < 0:
                subgraph.add_edge(u, v, key=k, attr_dict=graph.edge[u][v][k])


def opening_by_central_dogma(graph):
    """Infers the matching RNA for each protein and the gene for each RNA and miRNA, then collapses the corresponding
    gene node to its RNA/miRNA node, then possibly from RNA to protein if available.

    Equivalent to:

    >>> infer_central_dogma(graph)
    >>> collapse_by_central_dogma(graph)

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    """
    infer_central_dogma(graph)
    collapse_by_central_dogma(graph)


def opening_by_central_dogma_to_genes(graph):
    """Infers the matching RNA for each protein and the gene for each RNA and miRNA, then collapses the corresponding
    protein and RNA/miRNA nodes to the gene node.

    This function is equivalent to:

    >>> infer_central_dogma(graph)
    >>> collapse_by_central_dogma_to_genes(graph)

    This method is useful to help overcome issues with BEL curation, when curators sometimes haphazardly annotate
    entities as either a gene, RNA, or protein. There is possibly significant biological subtlty that can be lost
    during this process, but sometimes this must be done to overcome the noise introduced by these kinds of mistakes.

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    """
    infer_central_dogma(graph)
    collapse_by_central_dogma_to_genes(graph)
