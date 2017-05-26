# -*- coding: utf-8 -*-

"""
Data Services
-------------

Each python module in the web submodule should have functions that take a Flask app and add certain endpoints to it. 
These endpoints should expose data as JSON, and not rely on templates, since they should be usable by apps in other
packages and locations
"""

from . import constants
from .analysis_service import build_analysis_service
from .compilation_service import build_synchronous_compiler_service
from .curation_service import build_curation_service
from .database_service import build_database_service
from .dict_service import build_dictionary_service
from .github_login_service import build_github_login_service
from .parser_endpoint import build_parser_service
from .receiver_service import build_receiver_service
from .reporting_service import build_reporting_service
from .sitemap_endpoint import build_sitemap_endpoint
from .upload_service import build_pickle_uploader_service
