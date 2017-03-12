# -*- coding: utf-8 -*-

import logging

from pybel.canonicalize import calculate_canonical_name
from pybel.constants import CITATION, CITATION_AUTHORS
from ..constants import CNAME

__all__ = [
    'parse_authors',
    'serialize_authors',
    'add_canonical_names',
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
    """Adds a canonical name to each node's data dictionary if they are missing

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    """
    for node, data in graph.nodes_iter(data=True):
        if CNAME in data:
            log.debug('Canonical name already in dictionary for %s', data[CNAME])
            continue

        graph.node[node][CNAME] = calculate_canonical_name(graph, node)
