# -*- coding: utf-8 -*-

import logging
from collections import defaultdict

from pybel.constants import *
from .deletion import prune_central_dogma
from .inference import infer_central_dogma
from .. import pipeline

__all__ = [
    'collapse_nodes',
    'build_central_dogma_collapse_dict',
    'build_central_dogma_collapse_gene_dict',
    'collapse_by_central_dogma',
    'collapse_by_central_dogma_to_genes',
    'collapse_variants_to_genes',
    'opening_on_central_dogma',
]

log = logging.getLogger(__name__)


@pipeline.in_place_mutator
def collapse_nodes(graph, dict_of_sets_of_nodes):
    """Collapses all nodes in values to the key nodes in place

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param dict_of_sets_of_nodes: A dictionary of {node: set of nodes}
    :type dict_of_sets_of_nodes: dict
    """
    log.debug('collapsing %d groups', len(dict_of_sets_of_nodes))

    for key_node, value_nodes in dict_of_sets_of_nodes.items():
        for value_node in value_nodes:
            for successor in graph.successors_iter(value_node):
                for key, data in graph.edge[value_node][successor].items():
                    if key >= 0:
                        graph.add_edge(key_node, successor, attr_dict=data)
                    elif successor not in graph.edge[key_node] or key not in graph.edge[key_node][successor]:
                        graph.add_edge(key_node, successor, key=key, **{RELATION: unqualified_edges[-1 - key]})

            for predecessor in graph.predecessors_iter(value_node):
                for key, data in graph.edge[predecessor][value_node].items():
                    if key >= 0:
                        graph.add_edge(predecessor, key_node, attr_dict=data)
                    elif predecessor not in graph.pred[key_node] or key not in graph.edge[predecessor][key_node]:
                        graph.add_edge(predecessor, key_node, key=key, **{RELATION: unqualified_edges[-1 - key]})

            graph.remove_node(value_node)

    # Remove self edges
    for u, v, k in graph.edges(keys=True):
        if u == v:
            graph.remove_edge(u, v, k)


def build_central_dogma_collapse_dict(graph):
    """Builds a dictionary to direct the collapsing on the central dogma

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :return: A dictionary of {node: set of nodes}
    :rtype: dict
    """
    collapse_dict = defaultdict(set)
    r2p = {}

    for rna_node, protein_node, d in graph.edges_iter(data=True):
        if d[RELATION] != TRANSLATED_TO:
            continue

        collapse_dict[protein_node].add(rna_node)
        r2p[rna_node] = protein_node

    for gene_node, rna_node, d in graph.edges_iter(data=True):
        if d[RELATION] != TRANSCRIBED_TO:
            continue

        if rna_node in r2p:
            collapse_dict[r2p[rna_node]].add(gene_node)
        else:
            collapse_dict[rna_node].add(gene_node)

    return collapse_dict


def build_central_dogma_collapse_gene_dict(graph):
    """Builds a dictionary to direct the collapsing on the central dogma

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :return: A dictionary of {node: set of nodes}
    :rtype: dict
    """
    collapse_dict = defaultdict(set)
    r2g = {}

    for gene_node, rna_node, d in graph.edges_iter(data=True):
        if d[RELATION] != TRANSCRIBED_TO:
            continue

        collapse_dict[gene_node].add(rna_node)
        r2g[rna_node] = gene_node

    for rna_node, protein_node, d in graph.edges_iter(data=True):
        if d[RELATION] != TRANSLATED_TO:
            continue

        if rna_node not in r2g:
            raise ValueError('Should complete origin before running this function')

        collapse_dict[r2g[rna_node]].add(protein_node)

    return collapse_dict


@pipeline.in_place_mutator
def collapse_by_central_dogma(graph):
    """Collapses all nodes from the central dogma (GENE, RNA, PROTEIN) to PROTEIN, or most downstream possible entity,
    in place. This function wraps :func:`collapse_nodes` and :func:`build_central_dogma_collapse_dict`.

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    
    Equivalent to:
    
    >>> collapse_nodes(graph, build_central_dogma_collapse_dict(graph)) 
    """
    collapse_dict = build_central_dogma_collapse_dict(graph)
    collapse_nodes(graph, collapse_dict)


@pipeline.in_place_mutator
def collapse_by_central_dogma_to_genes(graph):
    """Collapses all nodes from the central dogma (:data:`pybel.constants.GENE`, :data:`pybel.constants.RNA`, 
    :data:`pybel.constants.MIRNA`, and :data:`pybel.constants.PROTEIN`) to :data:`pybel.constants.GENE` in place. This 
    function wraps :func:`collapse_nodes` and :func:`build_central_dogma_collapse_gene_dict`.
    
    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    
    Equivalent to:
    
    >>> collapse_nodes(graph, build_central_dogma_collapse_gene_dict(graph))
    """
    collapse_dict = build_central_dogma_collapse_gene_dict(graph)
    collapse_nodes(graph, collapse_dict)


@pipeline.in_place_mutator
def collapse_variants_to_genes(graph):
    """Finds all protein variants that are pointing to a gene and not a protein and fixes them by changing their
    function to be :data:`pybel.constants.GENE`

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    """
    for node, data in graph.nodes(data=True):
        if data[FUNCTION] != PROTEIN:
            continue
        if VARIANTS not in data:
            continue
        if any(d[RELATION] == TRANSCRIBED_TO for u, v, d in graph.in_edges_iter(data=True)):
            graph.node[node][FUNCTION] = GENE


@pipeline.in_place_mutator
def opening_on_central_dogma(graph):
    """Infers central dogmatic relations with :func:`infer_central_dogma` then successively prunes gene leaves then
    RNA leaves with :func:`prune_central_dogma` to connect disparate elements in a knowledge assembly

    :param graph: A BEL graph
    :type graph: pybel.BELGraph

    Equivalent to:

    >>> infer_central_dogma(graph)
    >>> prune_central_dogma(graph)

    """
    infer_central_dogma(graph)
    prune_central_dogma(graph)


@pipeline.in_place_mutator
def collapse_by_opening_on_central_dogma(graph):
    """Infers the matching RNA for each protein and the gene for each RNA and miRNA, then collapses the corresponding
    gene node to its RNA/miRNA node, then possibly from RNA to protein if available. Wraps :func:`infer_central_dogma`
    and :func:`collapse_by_central_dogma`.

    :param graph: A BEL graph
    :type graph: pybel.BELGraph

    Equivalent to:

    >>> infer_central_dogma(graph)
    >>> collapse_by_central_dogma(graph)
    """
    infer_central_dogma(graph)
    collapse_by_central_dogma(graph)


@pipeline.in_place_mutator
def collapse_by_opening_by_central_dogma_to_genes(graph):
    """Infers the matching RNA for each protein and the gene for each RNA and miRNA, then collapses the corresponding
    protein and RNA/miRNA nodes to the gene node.

    This method is useful to help overcome issues with BEL curation, when curators sometimes haphazardly annotate
    entities as either a gene, RNA, or protein. There is possibly significant biological subtlty that can be lost
    during this process, but sometimes this must be done to overcome the noise introduced by these kinds of mistakes.
    
    Wraps :func:`infer_central_dogma` and :func:`collapse_by_central_dogma_to_genes`.
    
    :param graph: A BEL graph
    :type graph: pybel.BELGraph

    Equivalent to:

    >>> infer_central_dogma(graph)
    >>> collapse_by_central_dogma_to_genes(graph)
    """
    infer_central_dogma(graph)
    collapse_by_central_dogma_to_genes(graph)
