# -*- coding: utf-8 -*-

"""This module contains functions that provide summaries of the errors encountered while parsing a BEL script"""

from collections import Counter, defaultdict


from pybel.constants import ANNOTATIONS
from pybel.parser.parse_exceptions import *
from ..utils import check_has_annotation

__all__ = [
    'count_error_types',
    'count_naked_names',
    'get_incorrect_names',
    'get_undefined_namespaces',
    'get_undefined_namespace_names',
    'calculate_incorrect_name_dict',
    'calculate_suggestions',
    'calculate_error_by_annotation',
    'group_errors',
]


def count_error_types(graph):
    """Counts the occurrence of each type of error in a graph

    :param pybel.BELGraph graph: A BEL graph
    :return: A Counter of {error type: frequency}
    :rtype: collections.Counter
    """
    return Counter(e.__class__.__name__ for _, _, e, _ in graph.warnings)


def count_naked_names(graph):
    """Counts the frequency of each naked name (names without namespaces)

    :param pybel.BELGraph graph: A BEL graph
    :return: A Counter from {name: frequency}
    :rtype: collections.Counter
    """
    return Counter(e.name for _, _, e, _ in graph.warnings if isinstance(e, NakedNameWarning))


def get_namespaces_with_incorrect_names(graph):
    """Returns the set of all namespaces with incorrect names in the graph"""
    return {
        e.namespace
        for _, _, e, _ in graph.warnings
        if isinstance(e, (MissingNamespaceNameWarning, MissingNamespaceRegexWarning))
    }


def get_incorrect_names(graph, namespace):
    """Returns the set of all incorrect names from the given namespace in the graph

    :param pybel.BELGraph graph: A BEL graph
    :param namespace: The namespace to filter by
    :type namespace: str
    :return: The set of all incorrect names from the given namespace in the graph
    :rtype: set[str]
    """
    return {
        e.name
        for _, _, e, _ in graph.warnings
        if isinstance(e, (MissingNamespaceNameWarning, MissingNamespaceRegexWarning)) and e.namespace == namespace
    }


def get_undefined_namespaces(graph):
    """Gets all namespaces that aren't actually defined
    
    :param pybel.BELGraph graph: A BEL graph
    :return: The set of all undefined namespaces
    :rtype: set[str]
    """
    return {
        e.namespace
        for _, _, e, _ in graph.warnings
        if isinstance(e, UndefinedNamespaceWarning)
    }


def get_undefined_namespace_names(graph, namespace):
    """Gets the names from a namespace that wasn't actually defined
    
    :param pybel.BELGraph graph: A BEL graph
    :param str namespace: The namespace to filter by
    :return: The set of all names from the undefined namespace
    :rtype: set[str]
    """
    return {
        e.name
        for _, _, e, _ in graph.warnings
        if isinstance(e, UndefinedNamespaceWarning) and e.namespace == namespace
    }


def get_undefined_annotations(graph):
    """Gets all annotations that aren't actually defined
    
    :param pybel.BELGraph graph: A BEL graph
    :return: The set of all undefined annotations
    :rtype: set[str]
    """
    return {
        e.annotation
        for _, _, e, _ in graph.warnings
        if isinstance(e, UndefinedAnnotationWarning)
    }


# FIXME need to change underlying definition and usage of this exception
def get_undefined_annotation_values(graph, annotation):
    """Gets the values from an annotation that wasn't actually defined

    :param pybel.BELGraph graph: A BEL graph
    :param str annotation: The annotaton to filter by
    :return: The set of all values from the undefined annotation
    :rtype: set[str]
    """
    raise NotImplementedError
    # return {e.value for _, _, e, _ in graph.warnings if isinstance(e, UndefinedAnnotationWarning) and e.annotation == annotation}


def calculate_incorrect_name_dict(graph):
    """Groups all of the incorrect identifiers in a dict of {namespace: list of erroneous names}

    :param pybel.BELGraph graph: A BEL graph
    :return: A dictionary of {namespace: list of erroneous names}
    :rtype: dict[str, str]
    """
    missing = defaultdict(list)

    for line_number, line, e, ctx in graph.warnings:
        if not isinstance(e, (MissingNamespaceNameWarning, MissingNamespaceRegexWarning)):
            continue
        missing[e.namespace].append(e.name)

    return dict(missing)


def calculate_suggestions(incorrect_name_dict, namespace_dict):
    """Uses fuzzy string matching to try and find the appropriate names for each of the incorrectly identified names

    :param incorrect_name_dict: A dictionary of {namespace: list of wrong names}
    :type incorrect_name_dict: dict
    :param namespace_dict: A dictionary of {namespace: list of allowed names}
    :type namespace_dict: dict
    :return: A dictionary of suggestions for each wrong (namespace, name) pair
    :rtype: dict
    """
    from fuzzywuzzy import process, fuzz

    suggestions_cache = defaultdict(list)

    for namespace in incorrect_name_dict:
        for name in incorrect_name_dict[namespace]:
            if (namespace, name) in suggestions_cache:
                continue

            for putative, score in process.extract(name, set(namespace_dict[namespace]),
                                                   scorer=fuzz.partial_token_set_ratio):
                suggestions_cache[namespace, name].append((putative, score))

    return dict(suggestions_cache)


def calculate_error_by_annotation(graph, annotation):
    """Groups the graph by a given annotation and builds lists of errors for each

    :param pybel.BELGraph graph: A BEL graph
    :param annotation: The annotation to group errors by
    :type annotation: str
    :return: A dictionary of {annotation value: list of errors}
    :rtype: dict[str, list[str]]
    """
    results = defaultdict(list)

    for line_number, line, e, context in graph.warnings:
        if not context or not check_has_annotation(context, annotation):
            continue

        values = context[ANNOTATIONS][annotation]

        if isinstance(values, str):
            results[values].append(e.__class__.__name__)
        elif isinstance(values, (set, tuple, list)):
            for value in values:
                results[value].append(e.__class__.__name__)

    return dict(results)


def group_errors(graph):
    """Groups the errors together for analysis of the most frequent error

    :param pybel.BELGraph graph: A BEL graph
    :return: A dictionary of {error string: list of line numbers}
    :rtype: dict[str, list[int]]
    """
    warning_summary = defaultdict(list)

    for ln, _, e, _ in graph.warnings:
        warning_summary[str(e)].append(ln)

    return dict(warning_summary)
