# -*- coding: utf-8 -*-

import os

import flask

from pybel.manager.cache import build_manager
from pybel.parser.parse_metadata import MetadataParser
from .constants import PYBEL_CACHE_CONNECTION, PYBEL_DEFINITION_MANAGER, PYBEL_METADATA_PARSER
from ..utils import build_template_environment, render_template_by_env

__all__ = [
    'set_cache_manager',
    'get_cache_manager',
    'set_metadata_parser',
    'get_metadata_parser',
    'load_managers',
]

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_ENVIRONMENT = build_template_environment(HERE)


def render_template(template_filename, **context):
    return render_template_by_env(TEMPLATE_ENVIRONMENT, template_filename, context=context)


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


def load_managers(app):
    """Retrieves the :data:`PYBEL_CACHE_CONNECTION` from a Flask app and uses it to add definition manager,
    metadata parser, and graph manager objects to the config.
    
    :param app: A Flask application 
    :type app: flask.Flask
    """
    connection = app.config.get(PYBEL_CACHE_CONNECTION)

    manager = build_manager(connection=connection)
    mdp = MetadataParser(manager=manager)

    set_cache_manager(app, manager)
    set_metadata_parser(app, mdp)
