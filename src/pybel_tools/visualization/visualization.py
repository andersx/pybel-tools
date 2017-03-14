# -*- coding: utf-8 -*-

"""

This module provides functions for making HTML visualizations of BEL Graphs

"""

from __future__ import print_function

import os

from pybel.io import to_jsons
from .utils import render_template
from ..mutation import add_canonical_names

__all__ = ['to_html', 'to_html_file', 'to_html_path']


def render_graph_template(context=None):
    """Renders the graph template as an HTML string

    :param context: The data dictionary to pass to the Jinja templating engine
    :type context: dict
    :rtype: str
    """
    return render_template('graph_template.html', context=context)


def build_graph_context(graph):
    """Builds the data dictionary to be used by the Jinja templating engine in :py:func:`to_html`

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :return: JSON context for rendering
    :rtype: dict
    """

    add_canonical_names(graph)

    return {
        'json': to_jsons(graph),
        'number_nodes': graph.number_of_nodes(),
        'number_edges': graph.number_of_edges()
    }


def to_html(graph):
    """Creates an HTML visualization for the given JSON representation of a BEL graph

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :return: HTML string representing the graph
    :rtype: str
    """
    return render_graph_template(context=build_graph_context(graph))


def to_html_file(graph, file):
    """Writes the HTML visualization to a file or file-like

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param file: A file or file-like
    :type file: file
    """
    print(to_html(graph), file=file)


def to_html_path(graph, path):
    """Writes the HTML visualization to a file specified by the file path

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param path: The file path
    :type path: str
    """
    with open(os.path.expanduser(path), 'w') as f:
        to_html_file(graph, f)
