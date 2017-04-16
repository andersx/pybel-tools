# -*- coding: utf-8 -*-

import logging

import flask
import requests
from flask import Flask

from pybel import from_json_dict, to_json_dict
from .utils import try_insert_graph, render_upload_error

log = logging.getLogger(__name__)

DEFAULT_SERVICE_URL = 'http://pybel.scai.fraunhofer.de'


def build_receiver_service(app, manager):
    """This service receives graphs as JSON requests, decodes, then uploads them

    :param app: A Flask application
    :type app: Flask
    :param manager: A PyBEL cache manager
    :type manager: pybel.manager.cache.CacheManager
    """

    @app.route('/api/receive', methods=['POST'])
    def receive():
        """Receives a JSON serialized BEL graph"""
        try:
            graph = from_json_dict(flask.request.get_json())
        except Exception as e:
            return render_upload_error(e)

        return try_insert_graph(manager, graph)

    log.info('Added receiver service to %s', app)


def post(graph, service=None):
    """Sends a graph to the receiver service and returns the :mod:`requests` response object
    
    :param pybel.BELGraph graph: A BEL graph
    :param str service: The location of the PyBEL web server. Defaults to :data:`DEFAULT_SERVICE_URL`
    :return: The response object from :mod:`requests` 
    :rtype: requests.Response
    """
    service = DEFAULT_SERVICE_URL if service is None else service
    url = service + '/api/receive'
    headers = {'content-type': 'application/json'}
    return requests.post(url, json=to_json_dict(graph), headers=headers)
