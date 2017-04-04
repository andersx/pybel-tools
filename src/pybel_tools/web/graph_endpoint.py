# -*- coding: utf-8 -*-

import logging

import flask
from flask import jsonify

from pybel.constants import METADATA_NAME, METADATA_VERSION
from .utils import get_graph_manager

__all__ = [
    'build_graph_endpoint',
]

log = logging.getLogger(__name__)


# TODO add getter function for given network in variety of formats @ddomingof @lekono @cthoyt
def build_graph_endpoint(app):
    """Adds common access to the graph cache

    :type app: flask.Flask
    """
    gcm = get_graph_manager(app)

    @app.route('/database/networks/')
    def list_networks():
        """Returns JSON of the network id's to their name and version"""
        return jsonify({gid: {METADATA_NAME: name, METADATA_VERSION: version} for gid, name, version in gcm.ls()})

    log.info('Added PyBEL Web graph endpoint to %s', app)
