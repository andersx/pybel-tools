# -*- coding: utf-8 -*-

from pybel.constants import *
from ..utils import build_template_environment, render_template_by_env

__all__ = [
    'render_template',
    'default_color_map'
]

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_ENVIRONMENT = build_template_environment(HERE)


def render_template(template_filename, context=None):
    return render_template_by_env(TEMPLATE_ENVIRONMENT, template_filename, context=context)


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
