# -*- coding: utf-8 -*-

"""
Node Filters
------------

A node filter is a function that takes two arguments: a :class:`pybel.BELGraph` and a node tuple. It returns a boolean
representing whether the node passed the given test.

This module contains a set of default functions for filtering lists of nodes and building node filtering functions.

A general use for a node filter function is to use the built-in :func:`filter` in code like
:code:`filter(your_node_filter, graph.nodes_iter())`
"""

from __future__ import print_function

from pybel.constants import FUNCTION, PATHOLOGY, OBJECT, SUBJECT, MODIFIER, ACTIVITY, NAMESPACE, NAME, DEGRADATION, \
    TRANSLOCATION
from ..constants import CNAME

__all__ = [
    'keep_node_permissive',
    'node_inclusion_filter_builder',
    'node_exclusion_filter_builder',
    'function_inclusion_filter_builder',
    'function_exclusion_filter_builder',
    'function_namespace_inclusion_builder',
    'namespace_inclusion_builder',
    'include_pathology_filter',
    'exclude_pathology_filter',
    'node_has_molecular_activity',
    'concatenate_node_filters',
    'filter_nodes',
    'count_passed_node_filter',
    'summarize_node_filter',
]


def filter_nodes(graph, node_filters=None):
    """Applies a set of filters to the nodes iterator of a BEL graph

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param node_filters: A node filter or list/tuple of node filters
    :type node_filters: types.FunctionType or iter[types.FunctionType]
    :return: An iterable of nodes that pass all filters
    :rtype: iter
    """

    # If no filters are given, return the standard node iterator
    if not node_filters:
        for node in graph.nodes_iter():
            yield node
    else:
        concatenated_filter = concatenate_node_filters(node_filters)
        for node in graph.nodes_iter():
            if concatenated_filter(graph, node):
                yield node


def count_passed_node_filter(graph, node_filters):
    """Counts how many nodes pass a given set of filters

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param node_filters: A node filter or list/tuple of node filters
    :type node_filters: types.FunctionType or iter[types.FunctionType]
    """
    return sum(1 for _ in filter_nodes(graph, node_filters))


def summarize_node_filter(graph, node_filters):
    """Prints a summary of the number of nodes passing a given set of filters

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param node_filters: A node filter or list/tuple of node filters
    :type node_filters: types.FunctionType or iter[types.FunctionType]
    """
    passed = count_passed_node_filter(graph, node_filters)
    print('{}/{} nodes passed {}'.format(passed, graph.number_of_nodes(), ', '.join(f.__name__ for f in node_filters)))


# Example filters

def keep_node_permissive(graph, node):
    """A default node filter that always evaluates to :data:`True`.

    Given BEL graph :code:`graph`, applying :func:`keep_node_permissive` with a filter on the nodes iterable
    as in :code:`filter(keep_node_permissive, graph.nodes_iter())` will result in the same iterable as
    :meth:`pybel.BELGraph.nodes_iter`

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param node: The node
    :type node: tuple
    :return: Always returns :data:`True`
    :rtype: bool
    """
    return True


def node_inclusion_filter_builder(nodes):
    """Builds a filter that only passes on nodes in the given list

    :param nodes: A list of BEL nodes
    :type nodes: list
    :return: A node filter (graph, node) -> bool
    :rtype: types.FunctionType
    """
    node_set = set(nodes)

    def inclusion_filter(graph, node):
        """Passes only for a node that is in the enclosed node list

        :param graph: A BEL Graph
        :type graph: pybel.BELGraph
        :param node: A BEL node
        :type node: tuple
        :return: If the node is contained within the enclosed node list
        :rtype: bool
        """
        return node in node_set

    return inclusion_filter


def node_exclusion_filter_builder(nodes):
    """Builds a filter that fails on nodes in the given list

    :param nodes: A list of nodes
    :type nodes: list
    :return: A node filter (graph, node) -> bool
    :rtype: types.FunctionType
    """
    node_set = set(nodes)

    def exclusion_filter(graph, node):
        """Passes only for a node that isn't in the enclosed node list

        :param graph: A BEL Graph
        :type graph: pybel.BELGraph
        :param node: A BEL node
        :type node: tuple
        :return: If the node isn't contained within the enclosed node list
        :rtype: bool
        """
        return node not in node_set

    return exclusion_filter


def function_inclusion_filter_builder(function):
    """Builds a filter that only passes on nodes of the given function(s)

    :param function: A BEL Function or list/set/tuple of BEL functions
    :type function: str or list or tuple or set
    :return: A node filter (graph, node) -> bool
    :rtype: types.FunctionType
    """

    if isinstance(function, str):
        def function_inclusion_filter(graph, node):
            """Passes only for a node that has the enclosed function

            :param graph: A BEL Graph
            :type graph: pybel.BELGraph
            :param node: A BEL node
            :type node: tuple
            :return: If the node doesn't have the enclosed function
            :rtype: bool
            """
            return graph.node[node][FUNCTION] == function

        return function_inclusion_filter

    elif isinstance(function, (list, tuple, set)):
        functions = set(function)

        def functions_inclusion_filter(graph, node):
            """Passes only for a node that is one of the enclosed functions

            :param graph: A BEL Graph
            :type graph: pybel.BELGraph
            :param node: A BEL node
            :type node: tuple
            :return: If the node doesn't have the enclosed functions
            :rtype: bool
            """
            return graph.node[node][FUNCTION] in functions

        return functions_inclusion_filter

    raise ValueError('Invalid type for argument: {}'.format(function))


def function_exclusion_filter_builder(function):
    """Builds a filter that fails on nodes of the given function(s)

    :param function: A BEL Function or list/set/tuple of BEL functions
    :type function: str or list or tuple or set
    :return: A node filter (graph, node) -> bool
    :rtype: types.FunctionType
    """

    if isinstance(function, str):
        def function_exclusion_filter(graph, node):
            """Passes only for a node that doesn't have the enclosed function

            :param graph: A BEL Graph
            :type graph: pybel.BELGraph
            :param node: A BEL node
            :type node: tuple
            :return: If the node doesn't have the enclosed function
            :rtype: bool
            """
            return graph.node[node][FUNCTION] != function

        return function_exclusion_filter

    elif isinstance(function, (list, tuple, set)):
        functions = set(function)

        def functions_exclusion_filter(graph, node):
            """Passes only for a node that doesn't have the enclosed functions

            :param graph: A BEL Graph
            :type graph: pybel.BELGraph
            :param node: A BEL node
            :type node: tuple
            :return: If the node doesn't have the enclosed functions
            :rtype: bool
            """
            return graph.node[node][FUNCTION] not in functions

        return functions_exclusion_filter

    raise ValueError('Invalid type for argument: {}'.format(function))


def function_namespace_inclusion_builder(function, namespace):
    if isinstance(namespace, str):
        def function_namespace_filter(graph, node):
            if function != graph.node[node][FUNCTION]:
                return False
            return NAMESPACE in graph.node[node] and graph.node[node][NAMESPACE] == namespace

        return function_namespace_filter

    elif isinstance(namespace, (list, tuple, set)):
        namespaces = set(namespace)

        def function_namespaces_filter(graph, node):
            if function != graph.node[node][FUNCTION]:
                return False
            return NAMESPACE in graph.node[node] and graph.node[node][NAMESPACE] in namespaces

        return function_namespaces_filter

    raise ValueError('Invalid type for argument: {}'.format(namespace))


def namespace_inclusion_builder(namespace):
    if isinstance(namespace, str):

        def namespace_filter(graph, node):
            return NAMESPACE in graph.node[node] and graph.node[node][NAMESPACE] == namespace

        return namespace_filter
    elif isinstance(namespace, (list, tuple, set)):
        namespaces = set(namespace)

        def namespaces_filter(graph, node):
            return NAMESPACE in graph.node[node] and graph.node[node][NAMESPACE] in namespaces

        return namespaces_filter

    raise ValueError('Invalid type for argument: {}'.format(namespace))


def data_contains_key_builder(key):
    """Builds a filter that passes only on nodes that have the given key in their data dictionary

        :param key: A key for the node's data dictionary
        :type key: str
        :return: A node filter (graph, node) -> bool
        :rtype: types.FunctionType
        """

    def data_contains_key(graph, node):
        """Passes only for a node that contains the enclosed key in its data dictionary

        :param graph: A BEL Graph
        :type graph: pybel.BELGraph
        :param node: A BEL node
        :type node: tuple
        :return: If the node contains the enclosed key in its data dictionary
        :rtype: bool
        """
        return key in graph.node[node]

    return data_contains_key


def data_missing_key_builder(key):
    """Builds a filter that passes only on nodes that don't have the given key in their data dictionary

    :param key: A key for the node's data dictionary
    :type key: str
    :return: A node filter (graph, node) -> bool
    :rtype: types.FunctionType
    """

    def data_does_not_contain_key(graph, node):
        """Passes only for a node that doesn't contain the enclosed key in its data dictionary

        :param graph: A BEL Graph
        :type graph: pybel.BELGraph
        :param node: A BEL node
        :type node: tuple
        :return: If the node doesn't contain the enclosed key in its data dictionary
        :rtype: bool
        """
        return key not in graph.node[node]

    return data_does_not_contain_key


#: Passes for nodes that have been annotated with a canonical name
node_has_cname = data_contains_key_builder(CNAME)

#: Fails for nodes that have been annotated with a canonical name
node_is_missing_cname = data_missing_key_builder(CNAME)


# Filter Builders

def concatenate_node_filters(filters=None):
    """Concatenates multiple node filters to a new filter that requires all filters to be met

    :param filters: a list of predicates (graph, node) -> bool
    :type filters: types.FunctionType or iter[types.FunctionType]
    :return: A combine filter (graph, node) -> bool
    :rtype: types.FunctionType

    Example usage:

    >>> from pybel.constants import GENE, PROTEIN, PATHOLOGY
    >>> path_filter = function_exclusion_filter_builder(PATHOLOGY)
    >>> app_filter = node_exclusion_filter_builder([(PROTEIN, 'HGNC', 'APP'), (GENE, 'HGNC', 'APP')])
    >>> my_filter = concatenate_node_filters([path_filter, app_filter])
    """

    # If no filters are given, then return the trivially permissive filter
    if not filters:
        return keep_node_permissive

    # If a filter outside a list is given, just return it
    if not isinstance(filters, (list, tuple, set)):
        return filters

    filters = list(filters)

    # If only one filter is given, don't bother wrapping it
    if 1 == len(filters):
        return filters[0]

    def concatenated_node_filter(graph, node):
        """Passes only for a nodes that pass all enclosed filters

        :param graph: A BEL Graph
        :type graph: pybel.BELGraph
        :param node: A BEL node
        :type node: tuple
        :return: If the node passes all enclosed filters
        :rtype: bool
        """
        return all(f(graph, node) for f in filters)

    return concatenated_node_filter


# Default Filters

#: A filter that passes for nodes that are :data:`pybel.constants.PATHOLOGY`
include_pathology_filter = function_inclusion_filter_builder(PATHOLOGY)

#: A filter that fails for nodes that are :data:`pybel.constants.PATHOLOGY`
exclude_pathology_filter = function_exclusion_filter_builder(PATHOLOGY)


def node_has_modifier(graph, node, modifier):
    """Returns true if over any of a nodes edges, it has a given modifier - :data:`pybel.constants.ACTIVITY`,
     :data:`pybel.constants.DEGRADATION`, or :data:`pybel.constants.TRANSLOCATION`.

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param node: A BEL node
    :type node: tuple
    :param str modifier: One of :data:`pybel.constants.ACTIVITY`, :data:`pybel.constants.DEGRADATION`, or 
                        :data:`pybel.constants.TRANSLOCATION`
    :return: If the node has a known modifier
    :rtype: bool
    """
    for _, _, d in graph.in_edges(node):
        if OBJECT in d and MODIFIER in d[OBJECT] and d[OBJECT][MODIFIER] == modifier:
            return True

    for _, _, d in graph.out_edges(node):
        if SUBJECT in d and MODIFIER in d[SUBJECT] and d[SUBJECT][MODIFIER] == modifier:
            return True

    return False


def node_has_molecular_activity(graph, node):
    """Returns true if over any of the node's edges it has a molecular activity

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param node: A BEL node
    :type node: tuple
    :return: If the node has a known molecular activity
    :rtype: bool
    """
    return node_has_modifier(graph, node, ACTIVITY)


def node_is_degraded(graph, node):
    """Returns true if over any of the node's edges it is degraded

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param node: A BEL node
    :type node: tuple
    :return: If the node has a known degradation
    :rtype: bool
    """
    return node_has_modifier(graph, node, DEGRADATION)


def node_is_translocated(graph, node):
    """Returns true if over any of the node's edges it is transloated

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param node: A BEL node
    :type node: tuple
    :return: If the node has a known translocation
    :rtype: bool
    """
    return node_has_modifier(graph, node, TRANSLOCATION)


def node_is_upstream_leaf(graph, node):
    """Returns if the node is an upstream leaf. An upstream leaf is defined as a node that has no in-edges, and exactly
    1 out-edge.

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param node: A BEL node
    :type node: tuple
    :return: If the node is an upstream leaf
    :rtype: bool
    """
    return 0 == len(graph.predecessors(node)) and 1 == len(graph.successors(node))


# TODO node filter that is false for abundances with no in-edges

def build_node_data_search(key, data_filter):
    """Passes for nodes who have the given key in their data dictionaries and whose associated values pass the given
    filter function

    :param key: The node data dictionary key to check
    :type key: str
    :param data_filter: 
    :type data_filter: types.FunctionType
    :return: 
    """

    def node_data_filter(graph, node):
        """Passes if the given node has a given data annotated and passes the contained filter
        
        :param graph: A BEL Graph
        :type graph: pybel.BELGraph
        :param node: A BEL node
        :type node: tuple
        :return: If the node has the contained key in its data dictionary and passes the contained filter
        :rtype: bool
        """
        return key in graph.node[node] and data_filter(graph.node[node][key])

    return node_data_filter


def build_node_key_search(query, key):
    """Builds a node filter that only passes for nodes whose values for the given key are superstrings of the query 
    string(s)
    
    :param query: The query string or strings to check if they're in the node name
    :type query: str or iter[str]
    :param key: The key for the node data dictionary. Should refer only to entries that have str values
    :type key: str
    """
    if isinstance(query, str):
        return build_node_data_search(key, lambda s: query.lower() in s.lower())
    elif isinstance(query, (list, tuple, set)):
        return build_node_data_search(key, lambda s: any(q.lower() in s.lower() for q in query))


def build_node_name_search(query):
    """Searches nodes' names. Is a thin wrapper around :func:`build_node_key_search` with 
    :data:`pybel.constants.NAME`
    """
    return build_node_key_search(query, NAME)


def build_node_cname_search(query):
    """Searches nodes' canonical names. Is a thin wrapper around :func:`build_node_key_search`"""
    return build_node_key_search(query, CNAME)
