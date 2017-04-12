# -*- coding: utf-8 -*-

import logging

import flask
from flask import jsonify

__all__ = [
    'build_definition_endpoint',
]

log = logging.getLogger(__name__)


def build_definition_endpoint(app, manager):
    """Adds common access to definitions cache
    
    :param app: A Flask application
    :type app: flask.Flask
    :param manager: A PyBEL cache manager
    :type manager: pybel.manager.cache.CacheManager
    """

    @app.route('/api/namespaces/bel')
    def list_cached_bel_namespaces():
        """Returns JSON of the BEL namespaces stored in memory"""
        return jsonify(manager.get_namespace_urls())

    @app.route('/api/namespaces/owl/')
    def list_cached_owl_namespaces():
        """Returns JSON of the OWL namespaces stored in memory"""
        return jsonify(manager.get_namespace_owl_urls())

    log.info('Added definitions endpoint to %s', app)
