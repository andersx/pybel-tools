# -*- coding: utf-8 -*-

"""This module contains functions to summarize the provenance (citations, evidences, and authors) in a BEL graph"""

import itertools as itt
from collections import defaultdict, Counter

from pybel.constants import *

__all__ = [
    'count_pmids'
]

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
