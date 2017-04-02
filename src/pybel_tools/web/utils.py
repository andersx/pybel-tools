# -*- coding: utf-8 -*-

import flask

from pybel.manager.cache import CacheManager
from pybel.manager.graph_cache import GraphCacheManager
from pybel.parser.parse_metadata import MetadataParser

PYBEL_CACHE_CONNECTION = 'pybel_cache_connection'
PYBEL_DEFINITION_MANAGER = 'pybel_definition_manager'
PYBEL_METADATA_PARSER = 'pybel_metadata_parser'
PYBEL_GRAPH_MANAGER = 'pybel_graph_manager'


def set_definition_manager(app, definition_manager):
    """Sets the definition cache manager associated with a given Flask app
    
    :param app: A Flask application
    :type app: flask.Flask
    :type definition_manager: pybel.manager.cache.CacheManager
    """
    app.config[PYBEL_DEFINITION_MANAGER] = definition_manager


def get_definition_manager(app):
    """Gets the definition cache manager associated with a given Flask app
    
    :param app: A Flask application
    :type app: flask.Flask
    :return: The app's definition manager
    :rtype: pybel.manager.cache.CacheManager
    """
    return app.config.get(PYBEL_DEFINITION_MANAGER)


def set_metadata_parser(app, metadata_parser):
    """Sets the metadata parser associated with a given Flask app

    :param app: A Flask application
    :type app: flask.Flask
    :type metadata_parser: pybel.parser.parse_metadata.MetadataParser
    """
    app.config[PYBEL_METADATA_PARSER] = metadata_parser


def get_metadata_parser(app):
    """Gets the metadata parser associated with a given Flask app

    :param app: A Flask application 
    :type app: flask.Flask
    :return: The app's metadata parser
    :rtype: pybel.parser.parse_metadata.MetadataParser
    """
    return app.config.get(PYBEL_METADATA_PARSER)


def set_graph_manager(app, graph_manager):
    """Sets the definition cache manager associated with a given Flask app
    
    :param app: A Flask application
    :type app: flask.Flask
    :type graph_manager: pybel.manager.graph_cache.GraphCacheManager
    """
    app.config[PYBEL_GRAPH_MANAGER] = graph_manager


def get_graph_manager(app):
    """Gets the definition cache manager associated with a given Flask app

    :param app: A Flask application
    :type app: flask.Flask
    :return: The app's graph manager
    :rtype: pybel.manager.graph_cache.GraphCacheManager
    """
    return app.config.get(PYBEL_GRAPH_MANAGER)


def load_managers(app):
    """Retrieves the :data:`PYBEL_CACHE_CONNECTION` from a Flask app and uses it to add definition manager,
    metadata parser, and graph manager objects to the config.
    
    :param app: A Flask application 
    :type app: flask.Flask
    """
    connection = app.config.get(PYBEL_CACHE_CONNECTION)

    cm = CacheManager(connection=connection)
    mdp = MetadataParser(cache_manager=cm)
    gcm = GraphCacheManager(connection=connection)

    set_definition_manager(app, cm)
    set_metadata_parser(app, mdp)
    set_graph_manager(app, gcm)
