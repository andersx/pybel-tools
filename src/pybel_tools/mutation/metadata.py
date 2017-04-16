# -*- coding: utf-8 -*-

import logging

from pybel.canonicalize import calculate_canonical_name
from pybel.constants import CITATION, CITATION_AUTHORS, CITATION_REFERENCE
from .. import pipeline
from ..citation_utils import get_citations_by_pmids
from ..constants import CNAME
from ..filters.edge_filters import edge_has_author_annotation, filter_edges, edge_has_pubmed_citation
from ..filters.node_filters import keep_missing_cname, filter_nodes
from ..summary.provenance import get_pmids

__all__ = [
    'parse_authors',
    'serialize_authors',
    'add_canonical_names',
    'fix_pubmed_citations'
]

log = logging.getLogger(__name__)


@pipeline.in_place_mutator
def parse_authors(graph):
    """Parses all of the citation author strings to lists by splitting on the pipe character "|"

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    """
    if 'PYBEL_PARSED_AUTHORS' in graph.graph:
        log.warning('Authors have already been parsed in %s', graph.graph)
        return

    for u, v, k, d in filter_edges(graph, edge_has_author_annotation):
        authors = d[CITATION][CITATION_AUTHORS]

        if not isinstance(authors, str):
            continue

        graph.edge[u][v][k][CITATION][CITATION_AUTHORS] = list(authors.split('|'))

    graph.graph['PYBEL_PARSED_AUTHORS'] = True


@pipeline.in_place_mutator
def serialize_authors(graph):
    """Recombines all authors with the pipe character "|"

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    """
    if 'PYBEL_PARSED_AUTHORS' not in graph.graph:
        log.warning('Authors have not yet been parsed in %s', graph.graph)
        return

    for u, v, k, d in filter_edges(graph, edge_has_author_annotation):
        authors = d[CITATION][CITATION_AUTHORS]

        if not isinstance(authors, list):
            continue

        graph.edge[u][v][k][CITATION][CITATION_AUTHORS] = '|'.join(authors)

    del graph.graph['PYBEL_PARSED_AUTHORS']


@pipeline.in_place_mutator
def add_canonical_names(graph):
    """Adds a canonical name to each node's data dictionary if they are missing, in place. 

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    """
    for node in filter_nodes(graph, keep_missing_cname):
        graph.node[node][CNAME] = calculate_canonical_name(graph, node)


@pipeline.in_place_mutator
def fix_pubmed_citations(graph, stringify_authors=False):
    """Overwrites all PubMed citations with values from NCBI's eUtils lookup service.

    Sets authors as list, so probably a good idea to run :func:`pybel_tools.mutation.serialize_authors` before
    exporting.

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param stringify_authors: Converts all author lists to author strings using
                              :func:`pybel_tools.mutation.serialize_authors`. Defaults to ``False``.
    :type stringify_authors: bool
    :return: A set of PMIDs for which the eUtils service crashed
    :rtype: set
    """
    pmids = get_pmids(graph)
    pmid_data, errors = get_citations_by_pmids(pmids, return_errors=True)

    for u, v, k, d in filter_edges(graph, edge_has_pubmed_citation):
        pmid = d[CITATION][CITATION_REFERENCE].strip()

        if pmid not in pmid_data:
            log.warning('PMID not valid: %s', pmid)
            errors.add(pmid)
            continue

        graph.edge[u][v][k][CITATION].update(pmid_data[pmid])

    if stringify_authors:
        serialize_authors(graph)

    return errors
