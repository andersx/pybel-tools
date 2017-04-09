# -*- coding: utf-8 -*-

import flask

from pybel.manager.cache import build_manager
from pybel.parser.parse_metadata import MetadataParser
from .constants import PYBEL_CACHE_CONNECTION, PYBEL_DEFINITION_MANAGER, PYBEL_METADATA_PARSER
from ..utils import build_template_renderer

__all__ = [
    'get_cache_connection',
    'set_cache_manager',
    'get_cache_manager',
    'set_metadata_parser',
    'get_metadata_parser',
]

render_template = build_template_renderer(__file__)


def get_cache_connection(app):
    """Gets the connection string from the configuration of the Flask app
    
    :param app: A Flask application
    :type app: flask.Flask
    """
    return app.config.get(PYBEL_CACHE_CONNECTION)


def set_cache_manager(app, definition_manager):
    """Sets the definition cache manager associated with a given Flask app
    
    :param app: A Flask application
    :type app: flask.Flask
    :type definition_manager: pybel.manager.cache.CacheManager
    """
    app.config[PYBEL_DEFINITION_MANAGER] = definition_manager


def get_cache_manager(app):
    """Gets the definition cache manager associated with a given Flask app
    
    :param app: A Flask application
    :type app: flask.Flask
    :return: The app's definition manager
    :rtype: pybel.manager.cache.CacheManager
    """
    if PYBEL_DEFINITION_MANAGER not in app.config:
        manager = build_manager(get_cache_connection(app))
        set_cache_manager(app, manager)

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
    if PYBEL_METADATA_PARSER not in app.config:
        mdp = MetadataParser(get_cache_manager(app))
        set_metadata_parser(app, mdp)

    return app.config.get(PYBEL_METADATA_PARSER)
