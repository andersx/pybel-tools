# -*- coding: utf-8 -*-
import logging

PYBEL_CACHE_CONNECTION = 'pybel_cache_connection'
PYBEL_DEFINITION_MANAGER = 'pybel_definition_manager'
PYBEL_METADATA_PARSER = 'pybel_metadata_parser'
PYBEL_GRAPH_MANAGER = 'pybel_graph_manager'
SECRET_KEY = 'SECRET_KEY'

PYBEL_GITHUB_CLIENT_ID = 'PYBEL_GITHUB_CLIENT_ID'
PYBEL_GITHUB_CLIENT_SECRET = 'PYBEL_GITHUB_CLIENT_SECRET'

integrity_message = "A graph with the same name ({}) and version ({}) already exists. If there have been changes since the last version, try bumping the version number."
reporting_log = logging.getLogger('pybelreporting')
