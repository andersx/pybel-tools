"""

This module contains functions useful throughout PyBEL Tools

"""
import itertools as itt
from collections import Counter, defaultdict

from pandas import DataFrame

from pybel.constants import ANNOTATIONS


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
    :type dict_of_counters: dict
    :return: A dictionary with the same keys as the input but the count of the length of the values
    :rtype: dict
    """
    return {k: len(v) for k, v in dict_of_counters.items()}


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


def calculate_tanimoto_set_distances(dict_of_sets):
    """Returns a distance matrix keyed by the keys in the given dict. Distances are calculated
    based on pairwise tanimoto similarity of the sets contained

    :param dict_of_sets: A dict of {x: set of y}
    :type dict_of_sets: dict
    :return: A distance matrix based on the set overlap (tanimoto) score between each x
    :rtype: pandas.DataFrame
    """
    result = defaultdict(dict)

    for x, y in itt.combinations(dict_of_sets, 2):
        result[x][y] = result[y][x] = len(dict_of_sets[x] & dict_of_sets[y]) / len(dict_of_sets[x] | dict_of_sets[y])

    for x in dict_of_sets:
        result[x][x] = 1

    return DataFrame.from_dict(dict(result))


def calculate_global_tanimoto_set_distances(dict_of_sets):
    """Calculates an alternative distance matrix based on the following equation:

    .. math:: distance(A, B)=1- \|A \cup B\| / \| \cup_{s \in S} s\|

    :param dict_of_sets: A dict of {x: set of y}
    :type dict_of_sets: dict
    :return: A distance matrix based on the
    :rtype: pandas.DataFrame
    """
    universe = set(itt.chain.from_iterable(dict_of_sets.values()))
    universe_size = len(universe)

    result = defaultdict(dict)

    for x, y in itt.combinations(dict_of_sets, 2):
        result[x][y] = result[y][x] = 1 - len(dict_of_sets[x] | dict_of_sets[y]) / universe_size

    for x in dict_of_sets:
        result[x][x] = 1 - len(x) / len(universe)

    return DataFrame.from_dict(dict(result))


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
