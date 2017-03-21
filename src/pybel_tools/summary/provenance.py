# -*- coding: utf-8 -*-

"""This module contains functions to summarize the provenance (citations, evidences, and authors) in a BEL graph"""

import itertools as itt
import logging
from collections import defaultdict, Counter

from pybel.constants import *
from ..utils import graph_edge_data_iter, count_defaultdict, check_has_annotation

__all__ = [
    'count_pmids',
    'get_pmids',
    'count_citations',
    'count_citations_by_annotation',
    'count_authors',
    'get_authors',
    'count_authors_by_annotation',
]

log = logging.getLogger(__name__)


def _generate_citation_dict(graph):
    """Prepares a citation data dictionary from a graph. This is a helper function

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :return: A dictionary of {citation type: {(reference, name) -> {set of (source node, target node)}}}
    :rtype: dict
    """
    results = defaultdict(lambda: defaultdict(set))

    for u, v, d in graph.edges_iter(data=True):
        c = d[CITATION]
        results[c[CITATION_TYPE]][u, v].add((c[CITATION_REFERENCE], c[CITATION_NAME]))

    return results


def has_pubmed_citation(edge_data_dictionary):
    """Checks if the edge data dictionary has a PubMed citation

    :param edge_data_dictionary: The edge data dictionary from a :class:`pybel.BELGraph`
    :type edge_data_dictionary: dict
    :return: Does the edge data dictionary has a PubMed citation?
    :rtype: bool
    """
    return CITATION in edge_data_dictionary and 'PubMed' == edge_data_dictionary[CITATION][CITATION_TYPE]


def get_pmids(graph):
    """Gets the set of all PubMed identifiers cited in the construction of a graph

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :return: A set of all PubMed identifiers cited in the construction of this graph
    :rtype: set
    """
    citations = set()
    for d in graph_edge_data_iter(graph):
        if not has_pubmed_citation(d):
            continue
        citations.add(d[CITATION][CITATION_REFERENCE])
    return citations


def count_pmids(graph):
    """Counts the frequency of PubMed documents in a graph

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :return: A Counter from {(pmid, name): frequency}
    :rtype: Counter
    """
    citations = _generate_citation_dict(graph)
    counter = Counter(itt.chain.from_iterable(citations['PubMed'].values()))
    return counter


def count_citations(graph, **annotations):
    """Counts the citations in a graph based on a given filter

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param annotations: The annotation filters to use
    :type annotations: dict
    :return: A counter from {(citation type, citation reference): frequency}
    :rtype: Counter
    """
    citations = defaultdict(set)

    for u, v, d in graph.edges_iter(data=True, **annotations):
        if CITATION not in d:
            continue

        c = d[CITATION]
        citations[u, v].add((c[CITATION_TYPE], c[CITATION_REFERENCE]))

    counter = Counter(itt.chain.from_iterable(citations.values()))

    return counter


def count_citations_by_annotation(graph, annotation='Subgraph'):
    """Groups the citation counters by subgraphs induced by the annotation

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param annotation: The annotation to use to group the graph
    :type annotation: str
    :return: A dictionary of Counters {subgraph name: Counter from {citation: frequency}}
    """
    citations = defaultdict(lambda: defaultdict(set))
    for u, v, d in graph.edges_iter(data=True):
        if not check_has_annotation(d, annotation) or CITATION not in d:
            continue

        c = d[CITATION]
        k = d[ANNOTATIONS][annotation]

        citations[k][u, v].add((c[CITATION_TYPE], c[CITATION_REFERENCE]))

    return {k: Counter(itt.chain.from_iterable(v.values())) for k, v in citations.items()}


def count_authors(graph):
    """Counts the contributions of each author to the given graph

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :return: A Counter from {author name: frequency}
    :rtype: Counter
    """
    authors = []

    for d in graph_edge_data_iter(graph):
        if CITATION not in d or CITATION_AUTHORS not in d[CITATION]:
            continue
        if isinstance(d[CITATION_AUTHORS], str):
            raise ValueError('Graph should be converyed with pybel.mutation.parse_authors first')
        authors.extend(d[CITATION_AUTHORS])

    return Counter(authors)


def get_authors(graph):
    """Gets the set of all authors in the given graph

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :return: A set of author names
    :rtype: set
    """
    authors = set()
    for d in graph_edge_data_iter(graph):
        if CITATION not in d or CITATION_AUTHORS not in d[CITATION]:
            continue
        if isinstance(d[CITATION_AUTHORS], str):
            raise ValueError('Graph should be converyed with pybel.mutation.parse_authors first')
        for author in d[CITATION_AUTHORS]:
            authors.add(author)
    return authors


def count_authors_by_annotation(graph, annotation='Subgraph'):
    """Groups the author counters by subgraphs induced by the annotation

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param annotation: The annotation to use to group the graph
    :type annotation: str
    :return: A dictionary of Counters {subgraph name: Counter from {author: frequency}}
    :rtype: dict
    """
    authors = defaultdict(list)
    for d in graph_edge_data_iter(graph):
        if not check_has_annotation(d, annotation) or CITATION not in d or CITATION_AUTHORS not in d[CITATION]:
            continue
        if isinstance(d[CITATION_AUTHORS], str):
            raise ValueError('Graph should be converyed with pybel.mutation.parse_authors first')
        for author in d[CITATION_AUTHORS]:
            authors[d[ANNOTATIONS][annotation]].append(author)
    return count_defaultdict(authors)
