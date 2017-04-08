# -*- coding: utf-8 -*-

"""
Edge Filters
------------

A edge filter is a function that takes five arguments: a :class:`pybel.BELGraph`, a source node tuple, a target node
tuple, a key, and a data dictionary. It returns a boolean representing whether the edge passed the given test.

This module contains a set of default functions for filtering lists of edges and building edge filtering functions.

A general use for an edge filter function is to use the built-in :func:`filter` in code like
:code:`filter(your_edge_filter, graph.edges_iter(keys=True, data=True))`
"""

from pybel.constants import CITATION_AUTHORS
from pybel.constants import RELATION, CAUSAL_RELATIONS, ANNOTATIONS, CITATION, CITATION_REFERENCE, CITATION_TYPE
from pybel.utils import subdict_matches
from ..constants import PUBMED
from ..utils import check_has_annotation

__all__ = [
    'keep_edge_permissive',
    'keep_causal_edges',
    'keep_has_author',
    'build_inverse_filter',
    'build_annotation_value_filter',
    'build_annotation_dict_filter',
    'build_citation_inclusion_filter',
    'build_citation_exclusion_filter',
    'build_author_inclusion_filter',
    'build_relation_filter',
    'concatenate_edge_filters',
    'filter_edges',
    'count_passed_edge_filter',
    'summarize_edge_filter'
]


def keep_edge_permissive(graph, u, v, k, d):
    """Passes for all edges

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param u: A BEL node
    :type u: tuple
    :param v: A BEL node
    :type v: tuple
    :param k: The edge key between the given nodes
    :type k: int
    :param d: The edge data dictionary
    :type d: dict
    :return: Always returns :code:`True`
    :rtype: bool
    """
    return True


def keep_causal_edges(graph, u, v, k, d):
    """Only passes on causal edges, belonging to the set :data:`pybel.constants.CAUSAL_RELATIONS`

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param u: A BEL node
    :type u: tuple
    :param v: A BEL node
    :type v: tuple
    :param k: The edge key between the given nodes
    :type k: int
    :param d: The edge data dictionary
    :type d: dict
    :return: True if the edge is a causal edge
    :rtype: bool
    """
    return graph.edge[u][v][k][RELATION] in CAUSAL_RELATIONS


def keep_has_author(graph, u, v, k, d):
    """Passes for edges that have citations with authors"""
    return CITATION in d and CITATION_AUTHORS in d[CITATION]


def keep_has_pubmed_citation(graph, u, v, k, d):
    """Passes for edges that have PubMed citations"""
    return CITATION in d and PUBMED == d[CITATION][CITATION_TYPE]


def build_inverse_filter(f):
    """Builds a filter that is the inverse of the given filter
    
    :param f: An edge filter function (graph, node, node, key, data) -> bool
    :type f: types.FunctionType
    :return: An edge filter function (graph, node, node, key, data) -> bool
    :rtype: types.FunctionType
    """

    def inverse_filter(graph, u, v, k, d):
        return not f(graph, u, v, k, d)

    return inverse_filter


def build_annotation_value_filter(annotation, value):
    """Builds a filter that only passes for edges that contain the given annotation and have the given value(s)
    
    :param annotation: The annotation to filter on
    :type annotation: str
    :param value: The value or values for the annotation to filter on
    :type value: str or iter[str]
    :return: An edge filter function (graph, node, node, key, data) -> bool
    :rtype: types.FunctionType
    """

    if isinstance(value, str):
        def annotation_value_filter(graph, u, v, k, d):
            """Only passes for edges that contain the given annotation and have the given value
    
            :param graph: A BEL Graph
            :type graph: pybel.BELGraph
            :param u: A BEL node
            :type u: tuple
            :param v: A BEL node
            :type v: tuple
            :param k: The edge key between the given nodes
            :type k: int
            :param d: The edge data dictionary
            :type d: dict
            :return: True if the edge has the contained annotation with the contained value
            :rtype: bool
            """
            if not check_has_annotation(graph.edge[u][v][k], annotation):
                return False
            return graph.edge[u][v][k][ANNOTATIONS][annotation] == value

        return annotation_value_filter
    elif isinstance(value, (list, set, tuple)):
        values = set(value)

        def annotation_values_filter(graph, u, v, k, d):
            """Only passes for edges that contain the given annotation and have one of the given values

            :param graph: A BEL Graph
            :type graph: pybel.BELGraph
            :param u: A BEL node
            :type u: tuple
            :param v: A BEL node
            :type v: tuple
            :param k: The edge key between the given nodes
            :type k: int
            :param d: The edge data dictionary
            :type d: dict
            :return: True if the edge has the contained annotation and one of the contained values
            :rtype: bool
            """
            if not check_has_annotation(graph.edge[u][v][k], annotation):
                return False
            return graph.edge[u][v][k][ANNOTATIONS][annotation] in values

        return annotation_values_filter


def build_annotation_dict_filter(annotations, partial_match=True):
    """Builds a filter that keeps edges whose data dictionaries are superdictionaries to the given dictionary"""

    def annotation_dict_filter(graph, u, v, k, d):
        """A filter that matches edges with the given dictionary as a subdictionary"""
        return subdict_matches(d, annotations, partial_match=partial_match)

    return annotation_dict_filter


def build_relation_filter(relations):
    """Builds a filter that passes only for edges with the given relation
    
    :param relations: A relation or iterable of relations
    :type relations: str or iter[str]
    :return: An edge filter function (graph, node, node, key, data) -> bool
    :rtype: types.FunctionType
    """

    if isinstance(relations, str):
        def relation_filter(graph, u, v, k, d):
            """Only passes for edges with the contained relation

            :param graph: A BEL Graph
            :type graph: pybel.BELGraph
            :param u: A BEL node
            :type u: tuple
            :param v: A BEL node
            :type v: tuple
            :param k: The edge key between the given nodes
            :type k: int
            :param d: The edge data dictionary
            :type d: dict
            :return: True if the edge has the contained relation
            :rtype: bool
            """
            return graph.edge[u][v][k][RELATION] == relations

        return relation_filter
    elif isinstance(relations, (list, tuple, set)):
        relation_set = set(relations)
        def relation_filter(graph, u, v, k, d):
            """Only passes for edges with one of the contained relations

            :param graph: A BEL Graph
            :type graph: pybel.BELGraph
            :param u: A BEL node
            :type u: tuple
            :param v: A BEL node
            :type v: tuple
            :param k: The edge key between the given nodes
            :type k: int
            :param d: The edge data dictionary
            :type d: dict
            :return: True if the edge has one of the contained relations
            :rtype: bool
            """
            return graph.edge[u][v][k][RELATION] in relation_set

        return relation_filter
    else:
        raise ValueError('Invalid type for argument: {}'.format(relations))


def build_citation_inclusion_filter(pmids):
    """Only passes for edges with citations whose references are one of the given PubMed identifiers
    
    :param pmids: A PubMed identifier or list of PubMed identifiers to filter for
    :type pmids: str or iter[str]
    :return: An edge filter function (graph, node, node, key, data) -> bool
    :rtype: types.FunctionType
    """

    if isinstance(pmids, str):
        def citation_inclusion_filter(graph, u, v, k, d):
            """Only passes for edges with PubMed citations matching the contained PubMed identifier

            :param graph: A BEL Graph
            :type graph: pybel.BELGraph
            :param u: A BEL node
            :type u: tuple
            :param v: A BEL node
            :type v: tuple
            :param k: The edge key between the given nodes
            :type k: int
            :param d: The edge data dictionary
            :type d: dict
            :return: True if the edge has a PubMed citation with the contained PubMed identifier
            :rtype: bool
            """
            return CITATION in d and PUBMED == d[CITATION][CITATION_TYPE] and d[CITATION][CITATION_REFERENCE] == pmids

        return citation_inclusion_filter

    else:
        pmids = set(pmids)

        def citations_inclusion_filter(graph, u, v, k, d):
            """Only passes for edges with PubMed citations matching one of the contained PubMed identifiers

            :param graph: A BEL Graph
            :type graph: pybel.BELGraph
            :param u: A BEL node
            :type u: tuple
            :param v: A BEL node
            :type v: tuple
            :param k: The edge key between the given nodes
            :type k: int
            :param d: The edge data dictionary
            :type d: dict
            :return: True if the edge has a PubMed citation with one of the contained PubMed identifiers
            :rtype: bool
            """
            return CITATION in d and PUBMED == d[CITATION][CITATION_TYPE] and d[CITATION][CITATION_REFERENCE] in pmids

        return citations_inclusion_filter


def build_citation_exclusion_filter(pmids):
    """Fails for edges with citations whose references are one of the given PubMed identifiers

    :param pmids: A PubMed identifier or list of PubMed identifiers to filter against
    :type pmids: str or iter[str]
    :return: An edge filter function (graph, node, node, key, data) -> bool
    :rtype: types.FunctionType
    """

    if isinstance(pmids, str):
        def citation_exclusion_filter(graph, u, v, k, d):
            """Fails for edges with PubMed citations matching the contained PubMed identifier

            :param graph: A BEL Graph
            :type graph: pybel.BELGraph
            :param u: A BEL node
            :type u: tuple
            :param v: A BEL node
            :type v: tuple
            :param k: The edge key between the given nodes
            :type k: int
            :param d: The edge data dictionary
            :type d: dict
            :return: True if the edge has a PubMed citation with the contained PubMed identifier
            :rtype: bool
            """
            return CITATION in d and PUBMED == d[CITATION][CITATION_TYPE] and d[CITATION][CITATION_REFERENCE] != pmids

        return citation_exclusion_filter

    else:
        pmids = set(pmids)

        def citations_exclusion_filter(graph, u, v, k, d):
            """Only passes for edges with PubMed citations matching one of the contained PubMed identifiers

            :param graph: A BEL Graph
            :type graph: pybel.BELGraph
            :param u: A BEL node
            :type u: tuple
            :param v: A BEL node
            :type v: tuple
            :param k: The edge key between the given nodes
            :type k: int
            :param d: The edge data dictionary
            :type d: dict
            :return: True if the edge has a PubMed citation with one of the contained PubMed identifiers
            :rtype: bool
            """
            return CITATION in d and PUBMED == d[CITATION][CITATION_TYPE] and d[CITATION][
                                                                                  CITATION_REFERENCE] not in pmids

        return citations_exclusion_filter


def build_author_inclusion_filter(authors):
    """Only passes for edges with author information that matches one of the given authors
    
    :param authors: The author or list of authors to filter by
    :type authors: str or iter[str]
    :return: An edge filter
    :rtype: types.FunctionType
    """
    if isinstance(authors, str):
        def author_filter(graph, u, v, k, d):
            """Only passes for edges with citations with an author that matches the contained author

            :param graph: A BEL Graph
            :type graph: pybel.BELGraph
            :param u: A BEL node
            :type u: tuple
            :param v: A BEL node
            :type v: tuple
            :param k: The edge key between the given nodes
            :type k: int
            :param d: The edge data dictionary
            :type d: dict
            :return: True if the edge has a citation with an author that matches the the contained author
            :rtype: bool
            """
            return CITATION in d and CITATION_AUTHORS in d[CITATION] and authors in d[CITATION][CITATION_AUTHORS]

        return author_filter

    else:
        author_set = set(authors)

        def author_filter(graph, u, v, k, d):
            """Only passes for edges with citations with an author that matches one or more of the contained authors

            :param graph: A BEL Graph
            :type graph: pybel.BELGraph
            :param u: A BEL node
            :type u: tuple
            :param v: A BEL node
            :type v: tuple
            :param k: The edge key between the given nodes
            :type k: int
            :param d: The edge data dictionary
            :type d: dict
            :return: True if the edge has a citation with an author that matches one or more of the contained authors
            :rtype: bool
            """
            return CITATION in d and CITATION_AUTHORS in d[CITATION] and any(
                author in d[CITATION][CITATION_AUTHORS] for author in author_set)

        return author_filter


def concatenate_edge_filters(filters):
    """Concatenates multiple edge filters to a new filter that requires all filters to be met.

    :param filters: a list of predicates (graph, node, node, key, data) -> bool
    :type filters: types.FunctionType or list[types.FunctionType] or tuple[types.FunctionType]
    :return: A combine filter (graph, node, node, key, data) -> bool
    :rtype: types.FunctionType
    """

    # If no filters are given, then return the trivially permissive filter
    if not filters:
        return keep_edge_permissive

    # If a filter outside a list is given, just return it
    if not isinstance(filters, (list, tuple)):
        return filters

    # If only one filter is given, don't bother wrapping it
    if 1 == len(filters):
        return filters[0]

    def concatenated_edge_filter(graph, u, v, k, d):
        """Passes only for an edge that pass all enclosed filters

        :param graph: A BEL Graph
        :type graph: pybel.BELGraph
        :param u: A BEL node
        :type u: tuple
        :param v: A BEL node
        :type v: tuple
        :param k: The edge key between the given nodes
        :type k: int
        :param d: The edge data dictionary
        :type d: dict
        :return: If the edge passes all enclosed filters
        :rtype: bool
        """
        return all(f(graph, u, v, k, d) for f in filters)

    return concatenated_edge_filter


def filter_edges(graph, filters):
    """Applies a set of filters to the edges iterator of a BEL graph

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param filters: A filter or list of filters
    :type filters: list or tuple or types.FunctionType
    :return: An iterable of edges that pass all filters
    :rtype: iter
    """

    # If no filters are given, return the standard edge iterator
    if not filters:
        for u, v, k, d in graph.edges_iter(keys=True, data=True):
            yield u, v, k, d
    else:
        concatenated_edge_filter = concatenate_edge_filters(filters)
        for u, v, k, d in graph.edges_iter(keys=True, data=True):
            if concatenated_edge_filter(graph, u, v, k, d):
                yield u, v, k, d


def count_passed_edge_filter(graph, filters):
    """Returns the number of edges passing a given set of filters

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param filters: A filter or list of filters
    :type filters: iter[types.FunctionType]
    :return: The number of edges passing a given set of filters
    :rtype: int
    """
    return sum(1 for _ in filter_edges(graph, filters))


def summarize_edge_filter(graph, filters):
    """Prints a summary of the number of edges passing a given set of filters

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param filters: A filter or list of filters
    :type filters: types.FunctionType or list[types.FunctionType]
    """
    passed = count_passed_edge_filter(graph, filters)
    print('{}/{} edges passed {}'.format(passed, graph.number_of_edges(), ', '.join(f.__name__ for f in filters)))
