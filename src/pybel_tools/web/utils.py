# -*- coding: utf-8 -*-

import flask

PYBEL_DEFINITION_MANAGER = 'pybel_definition_manager'
PYBEL_METADATA_PARSER = 'pybel_metadata_parser'
PYBEL_GRAPH_MANAGER = 'pybel_graph_manager'


def set_definition_manager(pybel_app, definition_manager):
    """Sets the definition cache manager associated with a given Flask app
    
    :type pybel_app: flask.Flask
    :type definition_manager: pybel.manager.cache.CacheManager
    """
    pybel_app.config[PYBEL_DEFINITION_MANAGER] = definition_manager


def get_definition_manager(pybel_app):
    """Gets the definition cache manager associated with a given Flask app
    
    :param pybel_app: 
    :type pybel_app: flask.Flask
    :return: 
    :rtype: pybel.manager.cache.CacheManager
    """
    return pybel_app.config.get(PYBEL_DEFINITION_MANAGER)


def set_metadata_parser(pybel_app, metadata_parser):
    """Sets the metadata parser associated with a given Flask app

    :type pybel_app: flask.Flask
    :type graph_manager: pybel.parser.parse_metadata.MetadataParser
    """
    pybel_app.config[PYBEL_METADATA_PARSER] = metadata_parser


def get_metadata_parser(pybel_app):
    """Gets the metadata parser associated with a given Flask app

    :param pybel_app: 
    :type pybel_app: flask.Flask
    :return: 
    :rtype: pybel.parser.parse_metadata.MetadataParser
    """
    return pybel_app.config.get(PYBEL_METADATA_PARSER)


def set_graph_manager(pybel_app, graph_manager):
    """Sets the definition cache manager associated with a given Flask app

    :type pybel_app: flask.Flask
    :type graph_manager: pybel.manager.graph_cache.GraphCacheManager
    """
    pybel_app.config[PYBEL_GRAPH_MANAGER] = graph_manager


def get_graph_manager(pybel_app):
    """Gets the definition cache manager associated with a given Flask app

    :param pybel_app: 
    :type pybel_app: flask.Flask
    :return: 
    :rtype: pybel.manager.graph_cache.GraphCacheManager
    """
    return pybel_app.config.get(PYBEL_GRAPH_MANAGER)
