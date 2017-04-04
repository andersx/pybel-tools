# -*- coding: utf-8 -*-

"""

This module provides functions for making HTML visualizations of BEL Graphs

"""

from __future__ import print_function

import json
import os

from pybel.io import to_jsons
from .utils import render_template, default_color_map
from ..mutation import add_canonical_names

__all__ = ['to_html', 'to_html_file', 'to_html_path']


def render_graph_template(context=None):
    """Renders the graph template as an HTML string

    :param context: The data dictionary to pass to the Jinja templating engine
    :type context: dict
    :rtype: str
    """
    return render_template('graph_template.html', context=context)


def build_graph_context(graph, color_map=None):
    """Builds the data dictionary to be used by the Jinja templating engine in :py:func:`to_html`

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param color_map: A dictionary from PyBEL internal node functions to CSS color strings like #FFEE00. Defaults
                    to :data:`default_color_map`
    :type color_map: dict
    :return: JSON context for rendering
    :rtype: dict
    """

    add_canonical_names(graph)

    color_map = default_color_map if color_map is None else color_map

    return {
        'json': to_jsons(graph),
        'cmap': json.dumps(color_map),
        'number_nodes': graph.number_of_nodes(),
        'number_edges': graph.number_of_edges()
    }


def to_html(graph, color_map=None):
    """Creates an HTML visualization for the given JSON representation of a BEL graph

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param color_map: A dictionary from PyBEL internal node functions to CSS color strings like #FFEE00. Defaults
                    to :data:`default_color_map`
    :type color_map: dict
    :return: HTML string representing the graph
    :rtype: str
    """
    return render_graph_template(context=build_graph_context(graph, color_map=color_map))


def to_html_file(graph, file, color_map=None):
    """Writes the HTML visualization to a file or file-like

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param color_map: A dictionary from PyBEL internal node functions to CSS color strings like #FFEE00. Defaults
                    to :data:`default_color_map`
    :type color_map: dict
    :param file: A file or file-like
    :type file: file
    """
    print(to_html(graph, color_map=color_map), file=file)


def to_html_path(graph, path, color_map=None):
    """Writes the HTML visualization to a file specified by the file path

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param color_map: A dictionary from PyBEL internal node functions to CSS color strings like #FFEE00. Defaults
                    to :data:`default_color_map`
    :type color_map: dict
    :param path: The file path
    :type path: str
    """
    with open(os.path.expanduser(path), 'w') as f:
        to_html_file(graph, f, color_map=color_map)
