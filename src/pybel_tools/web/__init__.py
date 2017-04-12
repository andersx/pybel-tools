# -*- coding: utf-8 -*-

"""
Data Services
-------------

Each python module in the web submodule should have functions that take a Flask app and add certain endpoints to it. 
These endpoints should expose data as JSON, and not rely on templates, since they should be usable by apps in other
packages and locations
"""

from . import constants
from . import definitions_endpoint
from . import graph_endpoint
from . import parser_endpoint
from .definitions_endpoint import *
from .graph_endpoint import *
from .parser_endpoint import *

__all__ = definitions_endpoint.__all__ + graph_endpoint.__all__ + parser_endpoint.__all__
