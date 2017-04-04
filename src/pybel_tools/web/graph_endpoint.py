# -*- coding: utf-8 -*-

import logging

import flask
from flask import jsonify

from pybel.constants import METADATA_NAME, METADATA_VERSION
from .utils import get_graph_manager, render_template

__all__ = [
    'build_graph_endpoint',
]

log = logging.getLogger(__name__)


# TODO add getter function for given network in variety of formats @ddomingof @lekono @cthoyt
def build_graph_endpoint(app):
    """Adds common access to the graph cache
    
    :param app: A Flask app
    :type app: flask.Flask
    """
    gcm = get_graph_manager(app)

    @app.route('/api/networks/list')
    def list_networks():
        """Returns JSON of the network id's to their name and version"""
        return jsonify({gid: {METADATA_NAME: name, METADATA_VERSION: version} for gid, name, version in gcm.ls()})

    log.info('Added PyBEL Web graph endpoint to %s', app)


def build_graph_viewer(app, prefix='/networks'):
    """Adds common access to the graph cache

    :param app: A Flask app
    :type app: flask.Flask
    :param prefix: The 
    :type prefix: str
    """
    gcm = get_graph_manager(app)

    @app.route('/networks/list')
    def list_networks_user():
        """Displays an HTML page for listing the networks"""
        return render_template('network_list.html', data=list(gcm.ls()), prefix=prefix)
