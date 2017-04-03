# -*- coding: utf-8 -*-

import jinja2

from pybel.constants import *

__all__ = [
    'render_template',
    'default_color_map'
]

HERE = os.path.dirname(os.path.abspath(__file__))

TEMPLATE_ENVIRONMENT = jinja2.Environment(
    autoescape=False,
    loader=jinja2.FileSystemLoader(os.path.join(HERE, 'templates')),
    trim_blocks=False
)

TEMPLATE_ENVIRONMENT.globals['STATIC_PREFIX'] = HERE + '/static/'


def render_template(template_filename, context=None):
    if context is None:
        context = {}
    return TEMPLATE_ENVIRONMENT.get_template(template_filename).render(context)


#: The color map defining the node colors in visualization
default_color_map = {
    PROTEIN: "#1F77B4",
    PATHOLOGY: "#FF7F0E",
    BIOPROCESS: "#2CA02C",
    MIRNA: "#D62728",
    COMPLEX: "#9467bd",
    COMPOSITE: "#9467bd",
    REACTION: "#8c564b",
    GENE: "#e377c2",
    ABUNDANCE: "#bcbd22",
    RNA: "#17becf"
}
