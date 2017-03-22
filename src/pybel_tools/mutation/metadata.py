# -*- coding: utf-8 -*-

import logging

from pybel.canonicalize import calculate_canonical_name
from pybel.constants import CITATION, CITATION_AUTHORS, CITATION_REFERENCE
from ..citation_utils import get_citations_by_pmids
from ..constants import CNAME
from ..summary.provenance import get_pmids, has_pubmed_citation

__all__ = [
    'parse_authors',
    'serialize_authors',
    'add_canonical_names',
    'fix_pubmed_citations'
]

log = logging.getLogger(__name__)


def parse_authors(graph):
    """Parses all of the citation author strings to lists by splitting on the pipe character "|"

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    """
    for u, v, k in graph.edges_iter(keys=True):
        if CITATION not in graph.edge[u][v][k]:
            continue

        if CITATION_AUTHORS not in graph.edge[u][v][k][CITATION]:
            continue

        authors = graph.edge[u][v][k][CITATION][CITATION_AUTHORS]

        if not isinstance(authors, str):
            continue

        graph.edge[u][v][k][CITATION][CITATION_AUTHORS] = list(authors.split('|'))


def serialize_authors(graph):
    """Recombines all authors with the pipe character "|"

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    """
    for u, v, k in graph.edges_iter(keys=True):
        if CITATION not in graph.edge[u][v][k]:
            continue

        if CITATION_AUTHORS not in graph.edge[u][v][k][CITATION]:
            continue

        authors = graph.edge[u][v][k][CITATION][CITATION_AUTHORS]

        if not isinstance(authors, list):
            continue

        graph.edge[u][v][k][CITATION][CITATION_AUTHORS] = '|'.join(authors)


def add_canonical_names(graph):
    """Adds a canonical name to each node's data dictionary if they are missing, in place

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    """
    for node, data in graph.nodes_iter(data=True):
        if CNAME in data:
            continue
        graph.node[node][CNAME] = calculate_canonical_name(graph, node)


def fix_pubmed_citations(graph, stringify_authors=False):
    """Overwrites all PubMed citations with values from NCBI's eUtils lookup service.

    Sets authors as list, so probably a good idea to run :func:`pybel_tools.mutation.serialize_authors` before
    exporting.

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param stringify_authors: Converts all author lists to author strings using
                              :func:`pybel_tools.mutation.serialize_authors`. Defaults to :code:`True`.
    :type stringify_authors: bool
    :return: A set of PMIDs for which the eUtils service crashed
    :rtype: set
    """
    pmids = get_pmids(graph)
    pmid_data, errors = get_citations_by_pmids(pmids, return_errors=True)
    for u, v, k, d in graph.edges_iter(data=True, keys=True):
        if not has_pubmed_citation(d):
            continue

        pmid = d[CITATION][CITATION_REFERENCE].strip()

        if pmid not in pmid_data:
            log.warning('PMID not valid: %s', pmid)
            errors.add(pmid)
            continue

        graph.edge[u][v][k][CITATION].update(pmid_data[pmid])

    if stringify_authors:
        serialize_authors(graph)

    return errors
