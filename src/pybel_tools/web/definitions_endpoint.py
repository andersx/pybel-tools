# -*- coding: utf-8 -*-

import flask
from flask import jsonify

from .utils import get_definition_manager, get_metadata_parser

__all__ = [
    'build_definition_endpoint',
]


def build_definition_endpoint(app):
    """Adds common access to definitions cache

    :type app: flask.Flask
    """
    dcm = get_definition_manager(app)
    mdp = get_metadata_parser(app)

    @app.route('/database/namespaces/')
    def list_stored_namespaces():
        """Returns JSON of the namespaces stored in the database"""
        return jsonify(dcm.get_namespace_urls() + dcm.get_namespace_owl_urls())

    @app.route('/memory/namespaces/bel/')
    def list_cached_bel_namespaces():
        """Returns JSON of the BEL namespaces stored in memory"""
        return jsonify(mdp.namespace_url_dict)

    @app.route('/memory/namespaces/owl/')
    def list_cached_bel_namespaces():
        """Returns JSON of the OWL namespaces stored in memory"""
        return jsonify(mdp.namespace_owl_dict)
