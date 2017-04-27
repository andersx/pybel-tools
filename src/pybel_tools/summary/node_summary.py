# -*- coding: utf-8 -*-

"""This module contains functions that provide summaries of the nodes in a graph"""

from collections import Counter, defaultdict

from pybel.constants import FUNCTION, NAMESPACE, NAME
from .error_summary import get_incorrect_names

__all__ = [
    'count_functions',
    'get_functions',
    'count_namespaces',
    'get_namespaces',
    'count_names',
    'get_names',
    'get_names_by_namespace'
]


def count_functions(graph):
    """Counts the frequency of each function present in a graph

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :return: A Counter from {function: frequency}
    :rtype: collections.Counter
    """
    return Counter(data[FUNCTION] for _, data in graph.nodes_iter(data=True))


def get_functions(graph):
    """Gets the set of all functions used in this graph

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :return: A set of functions
    :rtype: set[str]
    """
    return set(count_functions(graph))


def count_namespaces(graph):
    """Counts the frequency of each namespace across all nodes (that have namespaces)

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :return: A Counter from {namespace: frequency}
    :rtype: collections.Counter
    """
    return Counter(data[NAMESPACE] for _, data in graph.nodes_iter(data=True) if NAMESPACE in data)


def get_namespaces(graph):
    """Gets the set of all namespaces used in this graph

    :param pybel.BELGraph graph: A BEL graph
    :return: A set of namespaces
    :rtype: set[str]
    """
    return set(count_namespaces(graph))


def count_names(graph):
    """Counts all names through the graph by the NAME tag in the nodes' data dictionaries.

    This is useful to identify which nodes appear with the same name in multiple namespaces, or to identify variants

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :return: A Counter from {names: frequency}
    :rtype: collections.Counter
    """
    return Counter(data[NAME] for _, data in graph.nodes_iter(data=True) if NAME in data)


def get_names(graph, namespace):
    """Get the set of all of the names in a given namespace that are in the graph

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param namespace: A namespace
    :type namespace: str
    :return: A set of names belonging to the given namespace that are in the given graph
    :rtype: set[str]
    """

    return {data[NAME] for _, data in graph.nodes_iter(data=True) if NAMESPACE in data and data[NAMESPACE] == namespace}


def get_names_by_namespace(graph):
    """Get a dictionary of {namespace: set of names} present in the graph.

    Equivalent to:

    >>> {namespace: get_names(graph, namespace) for namespace in get_namespaces(graph)}

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :return: A dictionary of {namespace: set of names}
    :rtype: dict[str, set[str]]
    """
    result = defaultdict(set)

    for node, data in graph.nodes_iter(data=True):
        if NAMESPACE in data:
            result[data[NAMESPACE]].add(data[NAME])

    return dict(result)


def get_names_with_errors(graph, namespace):
    """Takes the names from the graph in a given namespace and the erroneous names from the same namespace and returns
    them together as a unioned set

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param namespace: The namespace to filter by
    :type namespace: str
    :return: The set of all correct and incorrect names from the given namespace in the graph
    :rtype: set[str]
    """
    return get_names(graph, namespace) | get_incorrect_names(graph, namespace)


def get_unused_namespaces(graph):
    """Gets all of the unused namespaces in a graph
    
    :param pybel.BELGraph graph: A BEL graph 
    :return: A set of namespaces that are included but not used
    :rtype: set[str]
    """
    used_namespaces = get_namespaces(graph)
    all_namespaces = set(graph.namespace_url) | set(graph.namespace_owl) | set(graph.namespace_pattern)
    return all_namespaces - used_namespaces
