"""

This module contains functions that provide aggregate summaries of graphs including visualization with matplotlib,
printing summary information, and exporting summarized graphs

"""

from __future__ import print_function

import networkx as nx
import pandas as pd

from pybel import to_pickle
from pybel.constants import *
from .edge_summary import count_relations, get_annotation_values
from .node_summary import count_functions
from ..selection import get_subgraph_by_annotation

__all__ = [
    'plot_summary_axes',
    'plot_summary',
    'info',
    'print_summary',
    'subgraphs_to_pickles',
]


def plot_summary_axes(graph, lax, rax):
    """Plots your graph summary statistics on the given axes.

    After, you should run :code:`plt.tight_layout()` and you must run :code:`plt.show()` to view.

    Shows:
    1. Count of nodes, grouped by function type
    2. Count of edges, grouped by relation type

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param lax: An axis object from matplotlib
    :param rax: An axis object from matplotlib

    Example usage:

    >>> import matplotlib.pyplot as plt
    >>> from pybel import from_pickle
    >>> from pybel_tools.summary import plot_summary_axes
    >>> graph = from_pickle('~/dev/bms/aetionomy/parkinsons.gpickle')
    >>> fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    >>> plot_summary_axes(graph, axes[0], axes[1])
    >>> plt.tight_layout()
    >>> plt.show()
    """

    ntc = count_functions(graph)
    etc = count_relations(graph)

    df = pd.DataFrame.from_dict(dict(ntc), orient='index')
    df_ec = pd.DataFrame.from_dict(dict(etc), orient='index')

    df.sort_values(0, ascending=True).plot(kind='barh', logx=True, ax=lax)
    lax.set_title('Number of nodes: {}'.format(graph.number_of_nodes()))

    df_ec.sort_values(0, ascending=True).plot(kind='barh', logx=True, ax=rax)
    rax.set_title('Number of edges: {}'.format(graph.number_of_edges()))


def plot_summary(graph, plt, **kwargs):
    """Plots your graph summary statistics. This function is a thin wrapper around :code:`plot_summary_axis`. It
    automatically takes care of building figures given matplotlib's pyplot module as an argument. After, you need
    to run :code:`plt.show()`.

    :code:`plt` is given as an argument to avoid needing matplotlib as a dependency for this function

    Shows:

    1. Count of nodes, grouped by function type
    2. Count of edges, grouped by relation type

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param plt: Give :code:`matplotlib.pyplot` to this parameter
    :param kwargs: keyword arguments to give to :func:`plt.subplots`

    Example usage:

    >>> import matplotlib.pyplot as plt
    >>> from pybel import from_pickle
    >>> from pybel_tools.summary import plot_summary
    >>> graph = from_pickle('~/dev/bms/aetionomy/parkinsons.gpickle')
    >>> plot_summary(graph, plt, figsize=(10, 4))
    >>> plt.show()

    """
    fig, axes = plt.subplots(1, 2, **kwargs)
    lax = axes[0]
    rax = axes[1]

    plot_summary_axes(graph, lax, rax)
    plt.tight_layout()

    return fig, axes


def info(graph):
    """Puts useful information about the graph in a string

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :rtype: str
    """
    s = '{}\n'.format(nx.info(graph))
    s += 'Network density: {}\n'.format(nx.density(graph))
    s += 'Number of weakly connected components: {}\n'.format(nx.number_weakly_connected_components(graph))
    return s


def print_summary(graph, file=None):
    """Prints useful information about the graph

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param file: A writeable file or file-like object. If None, defaults to :code:`sys.stdout`
    """
    print(info(graph), file=file)


def subgraphs_to_pickles(graph, directory, annotation='Subgraph'):
    """Groups the given graph into subgraphs by the given annotation with :func:`group_subgraphs` and outputs them
    as gpickle files to the given directory with :func:`pybel.to_pickle`

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param directory: A directory to output the pickles
    :type directory: str
    :param annotation: An annotation to split by. Suggestion: 'Subgraph'
    :type annotation: str
    """
    for value in get_annotation_values(graph, annotation):
        sg = get_subgraph_by_annotation(graph, annotation, value)
        sg.document.update(graph.document)

        file_name = '{}_{}.gpickle'.format(annotation, value.replace(' ', '_'))
        path = os.path.join(directory, file_name)
        to_pickle(sg, path)
