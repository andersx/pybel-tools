# -*- coding: utf-8 -*-

"""

Utilities for displaying graphs with inline HTML in Jupyter Notebooks

"""

from random import sample

from IPython.display import Javascript

from pybel.io import to_jsons
from .utils import render_template
from ..mutation import add_canonical_names

__all__ = ['to_jupyter', 'to_jupyter_str']

DEFAULT_WIDTH = 1000
DEFAULT_HEIGHT = 650


def generate_id():
    """Generates a random string of letters"""
    return "".join(sample('abcdefghjkmopqrstuvqxyz', 16))


def to_jupyter(graph, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    """Displays the BEL graph inline in a Jupyter notebook.

    To use successfully, make run as the last statement in a cell inside a Jupyter notebook.

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param width: The width of the visualization window to render
    :type width: int
    :param height: The height of the visualization window to render
    :type height: int
    :return:
    """
    return Javascript(to_jupyter_str(graph, width=width, height=height))


def to_jupyter_str(graph, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT):
    """Returns the string to be javascript-ified by the Jupyter notebook function :func:`IPython.display.Javascript`

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param width: The width of the visualization window to render
    :type width: int
    :param height: The height of the visualization window to render
    :type height: int
    :return: The javascript string to turn into magic
    :rtype: str
    """
    add_canonical_names(graph)
    gjson = to_jsons(graph)

    d3_code = render_template('pybel_vis.js')
    chart_id = generate_id()

    javascript_vars = """
        var chart = "{}";
        var width = {};
        var height = {};
        var graph = {};
    """.format(chart_id, width, height, gjson)

    require_code = """
        require.config({
          paths: {
              d3: '//cdnjs.cloudflare.com/ajax/libs/d3/4.5.0/d3.min'
          }
        });

        var elementInnerHTML = "<div id='" + chart + "'></div>";

        element.append(elementInnerHTML);

        var chartQualified = "#" + chart;

        require(['d3'], function(d3) {
            return init_d3_force(d3, graph, chartQualified, width, height);
        });
    """

    result = d3_code + javascript_vars + require_code

    return result
