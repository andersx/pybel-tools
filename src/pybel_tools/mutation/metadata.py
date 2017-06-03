# -*- coding: utf-8 -*-

import logging

from pybel.canonicalize import calculate_canonical_name
from pybel.constants import CITATION, CITATION_AUTHORS, CITATION_REFERENCE
from .. import pipeline
from ..citation_utils import get_citations_by_pmids
from ..constants import CNAME
from ..filters.edge_filters import edge_has_author_annotation, filter_edges, edge_has_pubmed_citation
from ..filters.node_filters import node_missing_cname, filter_nodes
from ..summary.edge_summary import get_annotations
from ..summary.node_summary import get_namespaces
from ..summary.provenance import get_pubmed_identifiers

__all__ = [
    'parse_authors',
    'serialize_authors',
    'add_canonical_names',
    'fix_pubmed_citations'
]

log = logging.getLogger(__name__)


@pipeline.in_place_mutator
def parse_authors(graph, force_parse=False):
    """Parses all of the citation author strings to lists by splitting on the pipe character "|"

    :param pybel.BELGraph graph: A BEL graph
    :param bool force_parse: Forces serialization without checking the tag
    """
    if not force_parse and 'PYBEL_PARSED_AUTHORS' in graph.graph:
        log.debug('Authors have already been parsed in %s', graph.name)
        return

    for u, v, k, d in filter_edges(graph, edge_has_author_annotation):
        authors = d[CITATION][CITATION_AUTHORS]

        if not isinstance(authors, str):
            continue

        graph.edge[u][v][k][CITATION][CITATION_AUTHORS] = list(authors.split('|'))

    graph.graph['PYBEL_PARSED_AUTHORS'] = True


@pipeline.in_place_mutator
def serialize_authors(graph, force_serialize=False):
    """Recombines all authors with the pipe character "|"

    :param pybel.BELGraph graph: A BEL graph
    :param bool force_serialize: Forces serialization without checking the tag
    """
    if not force_serialize and 'PYBEL_PARSED_AUTHORS' not in graph.graph:
        log.warning('Authors have not yet been parsed in %s', graph.name)
        return

    for u, v, k, d in filter_edges(graph, edge_has_author_annotation):
        authors = d[CITATION][CITATION_AUTHORS]

        if not isinstance(authors, list):
            continue

        graph.edge[u][v][k][CITATION][CITATION_AUTHORS] = '|'.join(authors)

    if 'PYBEL_PARSED_AUTHORS' in graph.graph:
        del graph.graph['PYBEL_PARSED_AUTHORS']


@pipeline.in_place_mutator
def add_canonical_names(graph):
    """Adds a canonical name to each node's data dictionary if they are missing, in place. 

    :param pybel.BELGraph graph: A BEL graph
    """
    for node in filter_nodes(graph, node_missing_cname):
        graph.node[node][CNAME] = calculate_canonical_name(graph, node)


@pipeline.in_place_mutator
def fix_pubmed_citations(graph, stringify_authors=False):
    """Overwrites all PubMed citations with values from NCBI's eUtils lookup service.

    Sets authors as list, so probably a good idea to run :func:`pybel_tools.mutation.serialize_authors` before
    exporting.

    :param pybel.BELGraph graph: A BEL graph
    :param bool stringify_authors: Converts all author lists to author strings using
                                  :func:`pybel_tools.mutation.serialize_authors`. Defaults to ``False``.
    :return: A set of PMIDs for which the eUtils service crashed
    :rtype: set
    """
    if 'PYBEL_ENRICHED_CITATIONS' in graph.graph:
        log.debug('citations have already been enriched in %s', graph.name)
        return

    pmids = get_pubmed_identifiers(graph)
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
    else:
        graph.graph['PYBEL_PARSED_AUTHORS'] = True

    graph.graph['PYBEL_ENRICHED_CITATIONS'] = True
    return errors


@pipeline.uni_in_place_mutator
def update_context(universe, graph):
    """Updates the context of a subgraph from the universe of all knowledge
    
    :param pybel.BELGraph universe: The universe of knowledge
    :param pybel.BELGraph graph: A BEL graph
    """
    for namespace in get_namespaces(graph):
        if namespace in universe.namespace_url:
            graph.namespace_url[namespace] = universe.namespace_url[namespace]
        elif namespace in universe.namespace_owl:
            graph.namespace_owl[namespace] = universe.namespace_owl[namespace]
        elif namespace in universe.namespace_owl:
            graph.namespace_pattern[namespace] = universe.namespace_pattern[namespace]
        else:
            log.warning('namespace: %s missing from universe', namespace)

    for annotation in get_annotations(graph):
        if annotation in universe.annotation_url:
            graph.annotation_url[annotation] = universe.annotation_url[annotation]
        elif annotation in universe.annotation_owl:
            graph.annotation_owl[annotation] = universe.annotation_owl[annotation]
        elif annotation in universe.annotation_owl:
            graph.annotation_pattern[annotation] = universe.annotation_pattern[annotation]
        else:
            log.warning('annotation: %s missing from universe', annotation)
