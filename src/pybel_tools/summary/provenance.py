# -*- coding: utf-8 -*-

"""This module contains functions to summarize the provenance (citations, evidences, and authors) in a BEL graph"""

import itertools as itt
import logging
from collections import defaultdict, Counter

from pybel.constants import *
from ..constants import PUBMED
from ..filters import filter_edges, build_pmid_inclusion_filter
from ..utils import graph_edge_data_iter, count_defaultdict, check_has_annotation, count_dict_values

__all__ = [
    'count_pmids',
    'get_pmids',
    'get_pmid_by_keyword',
    'count_citations',
    'count_citations_by_annotation',
    'count_authors',
    'count_author_publications',
    'get_authors',
    'get_authors_by_keyword',
    'count_authors_by_annotation',
    'get_evidences_by_pmid',
]

log = logging.getLogger(__name__)


def _generate_citation_dict(graph):
    """Prepares a citation data dictionary from a graph. This is a helper function

    :param pybel.BELGraph graph: A BEL graph
    :return: A dictionary of {citation type: {(reference, name) -> {set of (source node, target node)}}}
    :rtype: dict
    """
    results = defaultdict(lambda: defaultdict(set))

    for u, v, d in graph.edges_iter(data=True):
        if CITATION not in d:
            continue
        results[d[CITATION][CITATION_TYPE]][u, v].add(d[CITATION][CITATION_REFERENCE].strip())

    return dict(results)


def has_pubmed_citation(edge_data_dictionary):
    """Checks if the edge data dictionary has a PubMed citation

    :param edge_data_dictionary: The edge data dictionary from a :class:`pybel.BELGraph`
    :type edge_data_dictionary: dict
    :return: Does the edge data dictionary has a PubMed citation?
    :rtype: bool
    """
    return CITATION in edge_data_dictionary and PUBMED == edge_data_dictionary[CITATION][CITATION_TYPE]


def iter_pmids(graph):
    return (d[CITATION][CITATION_REFERENCE].strip() for d in graph_edge_data_iter(graph) if has_pubmed_citation(d))


def get_pmids(graph):
    """Gets the set of all PubMed identifiers cited in the construction of a graph

    :param pybel.BELGraph graph: A BEL graph
    :return: A set of all PubMed identifiers cited in the construction of this graph
    :rtype: set[str]
    """
    return set(iter_pmids(graph))


def get_pmid_by_keyword(keyword, graph=None, pmids=None):
    """Gets the set of PubMed identifiers beginning with the given keyword string
    
    :param pybel.BELGraph graph: A BEL graph
    :param keyword: The beginning of a PubMed identifier
    :type keyword: str
    :param pmids: A set of pre-cached PubMed identifiers
    :type pmids: set[str]
    :return: A set of PMIDs starting with the given string
    :rtype: set[str]
    """
    if pmids is not None:
        return {pmid for pmid in pmids if pmid.startswith(keyword)}

    if graph is None:
        raise ValueError('Graph not supplied')

    return {pmid for pmid in iter_pmids(graph) if pmid.startswith(keyword)}


def count_pmids(graph):
    """Counts the frequency of PubMed documents in a graph

    :param pybel.BELGraph graph: A BEL graph
    :return: A Counter from {(pmid, name): frequency}
    :rtype: collections.Counter
    """
    return Counter(iter_pmids(graph))


def count_citations(graph, **annotations):
    """Counts the citations in a graph based on a given filter

    :param pybel.BELGraph graph: A BEL graph
    :param annotations: The annotation filters to use
    :type annotations: dict
    :return: A counter from {(citation type, citation reference): frequency}
    :rtype: collections.Counter
    """
    citations = defaultdict(set)

    for u, v, d in graph.edges_iter(data=True, **annotations):
        if CITATION not in d:
            continue

        c = d[CITATION]
        citations[u, v].add((c[CITATION_TYPE], c[CITATION_REFERENCE].strip()))

    counter = Counter(itt.chain.from_iterable(citations.values()))
    return counter


def count_citations_by_annotation(graph, annotation='Subgraph'):
    """Groups the citation counters by subgraphs induced by the annotation

    :param pybel.BELGraph graph: A BEL graph
    :param annotation: The annotation to use to group the graph
    :type annotation: str
    :return: A dictionary of Counters {subgraph name: Counter from {citation: frequency}}
    """
    citations = defaultdict(lambda: defaultdict(set))
    for u, v, d in graph.edges_iter(data=True):
        if not check_has_annotation(d, annotation) or CITATION not in d:
            continue

        k = d[ANNOTATIONS][annotation]

        citations[k][u, v].add((d[CITATION][CITATION_TYPE], d[CITATION][CITATION_REFERENCE].strip()))

    return {k: Counter(itt.chain.from_iterable(v.values())) for k, v in citations.items()}


def count_authors(graph):
    """Counts the contributions of each author to the given graph

    :param pybel.BELGraph graph: A BEL graph
    :return: A Counter from {author name: frequency}
    :rtype: collections.Counter
    """
    authors = []
    for d in graph_edge_data_iter(graph):
        if CITATION not in d or CITATION_AUTHORS not in d[CITATION]:
            continue
        if isinstance(d[CITATION][CITATION_AUTHORS], str):
            raise ValueError('Graph should be converted with pbt.mutation.parse_authors first')
        for author in d[CITATION][CITATION_AUTHORS]:
            authors.append(author)

    return Counter(authors)


def count_author_publications(graph):
    """Counts the number of publications of each author to the given graph

    :param pybel.BELGraph graph: A BEL graph
    :return: A Counter from {author name: frequency}
    :rtype: collections.Counter
    """
    authors = defaultdict(list)
    for d in graph_edge_data_iter(graph):
        if CITATION not in d or CITATION_AUTHORS not in d[CITATION]:
            continue
        if isinstance(d[CITATION][CITATION_AUTHORS], str):
            raise ValueError('Graph should be converted with pbt.mutation.parse_authors first')
        for author in d[CITATION][CITATION_AUTHORS]:
            authors[author].append(d[CITATION][CITATION_REFERENCE].strip())

    return Counter(count_dict_values(count_defaultdict(authors)))

# TODO switch to use node filters
def get_authors(graph):
    """Gets the set of all authors in the given graph

    :param pybel.BELGraph graph: A BEL graph
    :return: A set of author names
    :rtype: set[str]
    """
    authors = set()
    for d in graph_edge_data_iter(graph):
        if CITATION not in d or CITATION_AUTHORS not in d[CITATION]:
            continue
        if isinstance(d[CITATION][CITATION_AUTHORS], str):
            raise ValueError('Graph should be converted with ``pbt.mutation.parse_authors`` first')
        for author in d[CITATION][CITATION_AUTHORS]:
            authors.add(author)
    return authors


def get_authors_by_keyword(keyword, graph=None, authors=None):
    """Gets authors for whom the search term is a substring
    
    :param graph: A BEL graph
    :type graph:
    :param keyword: The keyword to search the author strings for
    :type keyword: str
    :param authors: An optional set of pre-cached authors calculated from the graph
    :type authors: set[str]
    :return: A set of authors with the keyword as a substring
    :rtype: set[str]
    """
    keyword_lower = keyword.lower()

    if authors is not None:
        return {author for author in authors if keyword_lower in author.lower()}

    if graph is None:
        raise ValueError('Graph not supplied')

    return {author for author in get_authors(graph) if keyword_lower in author.lower()}


def count_authors_by_annotation(graph, annotation='Subgraph'):
    """Groups the author counters by subgraphs induced by the annotation

    :param pybel.BELGraph graph: A BEL graph
    :param annotation: The annotation to use to group the graph
    :type annotation: str
    :return: A dictionary of Counters {subgraph name: Counter from {author: frequency}}
    :rtype: dict
    """
    authors = defaultdict(list)
    for d in graph_edge_data_iter(graph):
        if not check_has_annotation(d, annotation) or CITATION not in d or CITATION_AUTHORS not in d[CITATION]:
            continue
        if isinstance(d[CITATION][CITATION_AUTHORS], str):
            raise ValueError('Graph should be converted with pybel.mutation.parse_authors first')
        for author in d[CITATION][CITATION_AUTHORS]:
            authors[d[ANNOTATIONS][annotation]].append(author)
    return count_defaultdict(authors)


def get_evidences_by_pmid(graph, pmids):
    """Gets a dictionary from the given PubMed identifiers to the sets of all evidence strings associated with each
    in the graph

    :param pybel.BELGraph graph: A BEL graph
    :param pmids: An iterable of PubMed identifiers, as strings. Is consumed and converted to a set.
    :type pmids: str or iter[str]
    :return: A dictionary of {pmid: set of all evidence strings}
    :rtype: dict
    """
    result = defaultdict(set)

    for _, _, _, d in filter_edges(graph, build_pmid_inclusion_filter(pmids)):
        result[d[CITATION][CITATION_REFERENCE]].add(d[EVIDENCE])

    return dict(result)
