"""

Utilities for displaying graphs with inline HTML in Jupyter Notebooks

"""

from random import sample

from IPython.display import Javascript

from pybel.io import to_jsons
from .utils import render_template

__all__ = ['to_jupyter']

def generate_id():
    """Generates a random string of letters"""
    return "".join(sample('abcdefghjkmopqrstuvqxyz', 16))


def to_jupyter(graph, width=1000, height=600):
    """Displays the BEL graph inline in a Jupyter notebook.

    To use successfully, make run as the last statement in a cell inside a jupyter notebook.

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param width: The width of the visualization window to render
    :type width: int
    :param height: The height of the visualization window to render
    :type height: int
    :return:
    """
    d3_code = render_template('pybel_vis.js')

    gjson = to_jsons(graph)

    chart_id = generate_id()

    javascript_vars = "var chart_idx='{}', graphx={}, widthx={}, heightx={};".format(chart_id, gjson, width, height)
    require_code = """
        require.config({
              paths: {
                  d3: '//cdnjs.cloudflare.com/ajax/libs/d3/3.4.8/d3.min'
              }
            });

        element.append("<div id='" + chart_idx + "'></div>");

        require(['d3'], function(d3) {
            show_bel_graph(d3, graphx, chart_idx,  widthx, heightx)
        });
    """

    result = javascript_vars + d3_code + require_code

    return Javascript(result)
