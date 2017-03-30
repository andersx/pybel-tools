# -*- coding: utf-8 -*-

"""This module contains functions useful throughout PyBEL Tools"""

import itertools as itt
from collections import Counter, defaultdict

import pandas as pd

from pybel.constants import ANNOTATIONS, CITATION_TYPE, CITATION_NAME, CITATION_REFERENCE, CITATION_DATE, \
    CITATION_AUTHORS, CITATION_COMMENTS, RELATION


def graph_edge_data_iter(graph):
    """Iterates over the edge data dictionaries

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :return: An iterator over the edge dictionaries in the graph
    :rtype: iter
    """
    for _, _, d in graph.edges_iter(data=True):
        yield d


def count_defaultdict(dict_of_lists):
    """Takes a dictionary and applies a counter to each list

    :param dict_of_lists: A dictionary of lists
    :type dict_of_lists: dict or defaultdict
    :return: A dictionary of {key: Counter(values)}
    :rtype: dict
    """
    return {k: Counter(v) for k, v in dict_of_lists.items()}


def get_value_sets(dict_of_iterables):
    """Takes a dictionary of lists/iterables/counters and gets the sets of the values

    :param dict_of_iterables: A dictionary of lists
    :type dict_of_iterables: dict or defaultdict
    :return: A dictionary of {key: set of values}
    :rtype: dict
    """
    return {k: set(v) for k, v in dict_of_iterables.items()}


def count_dict_values(dict_of_counters):
    """Counts the number of elements in each value (can be list, Counter, etc)

    :param dict_of_counters: A dictionary of things whose lengths can be measured (lists, Counters, dicts)
    :type dict_of_counters: dict or defaultdict
    :return: A Counter with the same keys as the input but the count of the length of the values list/tuple/set/Counter
    :rtype: collections.Counter
    """
    return Counter({k: len(v) for k, v in dict_of_counters.items()})


def _check_has_data(d, sd, key):
    return sd in d and key in d[sd]


def check_has_annotation(data, key):
    """Checks that ANNOTATION is included in the data dictionary and that the key is also present

    :param data: The data dictionary from a BELGraph's edge
    :type data: dict
    :param key: An annotation key
    :param key: str
    :return: If the annotation key is present in the current data dictionary
    :rtype: bool

    For example, it might be useful to print all edges that are annotated with 'Subgraph':

    >>> from pybel import BELGraph
    >>> graph = BELGraph()
    >>> ...
    >>> for u, v, data in graph.edges_iter(data=True):
    >>>     if not check_has_annotation(data, 'Subgraph')
    >>>         continue
    >>>     print(u, v, data)
    """
    return _check_has_data(data, ANNOTATIONS, key)


def set_percentage(x, y):
    """What percentage of x is contained within y?

    :param x: A set
    :type x: set
    :param y: Another set
    :type y: set
    :return: The percentage of x contained within y
    :rtype: float
    """
    a, b = set(x), set(y)

    if not a:
        return 0.0

    return len(a & b) / len(a)


def tanimoto_set_similarity(x, y):
    """Calculates the tanimoto set similarity

    :param x: A set
    :type x: set
    :param y: Another set
    :type y: set
    :return: The similarity between
    :rtype: float
    """
    a, b = set(x), set(y)
    union = a | b

    if not union:
        return 0.0

    return len(a & b) / len(union)


def calculate_single_tanimoto_set_distances(target, dict_of_sets):
    """Returns a dictionary of distances keyed by the keys in the given dict. Distances are calculated
    based on pairwise tanimoto similarity of the sets contained

    :param target: A set
    :type target: set
    :param dict_of_sets: A dict of {x: set of y}
    :type dict_of_sets: dict
    :return: A similarity dicationary based on the set overlap (tanimoto) score between the target set and the sets in
            dos
    :rtype: dict
    """
    target_set = set(target)
    return {k: tanimoto_set_similarity(target_set, s) for k, s in dict_of_sets.items()}


def calculate_tanimoto_set_distances(dict_of_sets):
    """Returns a distance matrix keyed by the keys in the given dict. Distances are calculated
    based on pairwise tanimoto similarity of the sets contained

    :param dict_of_sets: A dict of {x: set of y}
    :type dict_of_sets: dict
    :return: A similarity matrix based on the set overlap (tanimoto) score between each x as a dict of dicts
    :rtype: dict
    """
    result = defaultdict(dict)

    for x, y in itt.combinations(dict_of_sets, 2):
        result[x][y] = result[y][x] = tanimoto_set_similarity(dict_of_sets[x], dict_of_sets[y])

    for x in dict_of_sets:
        result[x][x] = 1.0

    return dict(result)


def calculate_global_tanimoto_set_distances(dict_of_sets):
    """Calculates an alternative distance matrix based on the following equation:

    .. math:: distance(A, B)=1- \|A \cup B\| / \| \cup_{s \in S} s\|

    :param dict_of_sets: A dict of {x: set of y}
    :type dict_of_sets: dict
    :return: A similarity matrix based on the alternative tanimoto distance as a dict of dicts
    :rtype: dict
    """
    universe = set(itt.chain.from_iterable(dict_of_sets.values()))
    universe_size = len(universe)

    result = defaultdict(dict)

    for x, y in itt.combinations(dict_of_sets, 2):
        result[x][y] = result[y][x] = 1.0 - len(dict_of_sets[x] | dict_of_sets[y]) / universe_size

    for x in dict_of_sets:
        result[x][x] = 1.0 - len(x) / universe_size

    return dict(result)


def all_edges_iter(graph, u, v):
    """Lists all edges between the given nodes

    :param graph: A BEL Graph
    :param graph: pybel.BELGraph
    :param u: A BEL node
    :param v: A BEL node
    :return: A list of (node, node, key)
    :rtype: list
    """
    if u not in graph.edge or v not in graph.edge[u]:
        raise ValueError('Graph has no edges')

    for k in graph.edge[u][v].keys():
        yield u, v, k


def barh(d, plt, title=None):
    """A convenience function for plotting a horizontal bar plot from a Counter"""
    labels = sorted(d, key=d.get)
    index = range(len(labels))

    plt.yticks(index, labels)
    plt.barh(index, [d[v] for v in labels])

    if title is not None:
        plt.title(title)


def barv(d, plt, title=None, rotation='vertical'):
    """A convenience function for plotting a vertical bar plot from a Counter"""
    labels = sorted(d, key=d.get, reverse=True)
    index = range(len(labels))
    plt.xticks(index, labels, rotation=rotation)
    plt.bar(index, [d[v] for v in labels])

    if title is not None:
        plt.title(title)


def citation_to_tuple(citation):
    """Converts a citation dictionary to a tuple. Can be useful for sorting and serialization purposes

    :param citation: A citation dictionary
    :type citation: dict
    :return: A citation tuple
    :rtype: tuple
    """
    return tuple([
        citation.get(CITATION_TYPE),
        citation.get(CITATION_NAME),
        citation.get(CITATION_REFERENCE),
        citation.get(CITATION_DATE),
        citation.get(CITATION_AUTHORS),
        citation.get(CITATION_COMMENTS)
    ])


def is_edge_consistent(graph, u, v):
    """Checks if all edges between two nodes have the same relation

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param u: The source BEL node
    :type u: tuple
    :param v: The target BEL node
    :type v: tuple
    :return: If all edges from the source to target node have the same relation
    :rtype: bool
    """
    if not graph.has_edge(u, v):
        raise ValueError('{} does not contain an edge ({}, {})'.format(graph, u, v))

    return 0 == len(set(d[RELATION] for d in graph.edge[u][v].values()))


def safe_add_edge(graph, u, v, key, attr_dict, **attr):
    """Adds an edge while preserving negative keys, and paying no respect to positive ones

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param u: The source BEL node
    :type u: tuple
    :param v: The target BEL node
    :type v: tuple
    :param key: The edge key. If less than zero, corresponds to an unqualified edge, else is disregarded
    :type key: int
    :param attr_dict: The edge data dictionary
    :type attr_dict: dict
    :param attr: Edge data to assign via keyword arguments
    :type attr: dict
    """
    if key < 0:
        graph.add_edge(u, v, key=key, attr_dict=attr_dict, **attr)
    else:
        graph.add_edge(u, v, attr_dict=attr_dict, **attr)


def load_differential_gene_expression(data_path, gene_symbol_column='Gene.symbol', logfc_column='logFC'):
    """Quick and dirty loader for differential gene expression data
    
    :return: A dictionary of {gene symbol: log fold change}
    :rtype: dict
    """
    df = pd.read_csv(data_path)
    df = df.loc[df[gene_symbol_column].notnull(), [gene_symbol_column, logfc_column]]
    return {k: v for _, k, v in df.itertuples()}
