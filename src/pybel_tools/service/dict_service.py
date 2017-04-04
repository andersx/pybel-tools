# -*- coding: utf-8 -*-

"""This module runs the dictionary-backed PyBEL API"""

import logging

import flask
from flask import Flask
import networkx as nx

from pybel import to_cx_json, to_graphml, to_bytes, to_bel_lines, to_json_dict, to_csv
from .dict_service_utils import DictionaryService
from ..summary import get_annotation_values_by_annotation

try:
    from StringIO import StringIO
    from BytesIO import BytesIO
except ImportError:
    from io import StringIO, BytesIO

log = logging.getLogger(__name__)

APPEND_PARAM = 'append'
REMOVE_PARAM = 'remove'
SOURCE_NODE = 'source'
TARGET_NODE = 'target'
SUPER_NETWORK = 'supernetwork'
DICTIONARY_SERVICE = 'dictionary_service'
BLACK_LIST = {APPEND_PARAM, REMOVE_PARAM, SOURCE_NODE, TARGET_NODE}


def get_dict_service(dsa):
    """Gets the latent PyBEL Dictionary Service from a Flask app

    :param dsa: A Flask app
    :type dsa: Flask
    :return: The latent dictionary service
    :rtype: DictionaryService
    """
    return dsa.config[DICTIONARY_SERVICE]


def set_dict_service(app, service):
    """Adds the dictionary service to the config of the given Flask app
    
    :param app: A Flask app
    :type app: flask.Flask
    :param service: The Dictionary Service
    :type service: DictionaryService
    """
    app.config[DICTIONARY_SERVICE] = service


def build_dictionary_service_app(app):
    """Builds the PyBEL Dictionary-Backed API Service. Adds a latent PyBEL Dictionary service that can be retrieved
    with :func:`get_dict_service`

    :param app: A Flask App
    :type app: Flask
    """

    api = DictionaryService()

    set_dict_service(app, api)

    def process_request(network_id, args):
        """
        Process the GET request returning the filtered graph
        :param network_id: id of the network
        :param args: flask.request.args
        :return:
        """
        # Convert from list of hashes (as integers) to node tuples
        expand_nodes = args.get(APPEND_PARAM)
        remove_nodes = args.get(REMOVE_PARAM)
        if expand_nodes:
            expand_nodes = [api.nid_node[int(h)] for h in expand_nodes.split(',')]

        if remove_nodes:
            remove_nodes = [api.nid_node[int(h)] for h in remove_nodes.split(',')]

        annotations = {k: args.getlist(k) for k in args if
                       k not in BLACK_LIST}

        graph = api.query_filtered_builder(network_id, expand_nodes, remove_nodes, **annotations)

        return graph

    @app.route('/')
    def list_networks():
        data = [(nid, n.name, n.version) for nid, n in api.networks.items()]
        return flask.render_template('network_list.html', data=data)

    @app.route('/network/filter/<int:network_id>', methods=['GET'])
    def get_filter(network_id):
        graph = api.get_network_by_id(network_id)

        unique_annotation_dict = get_annotation_values_by_annotation(graph)

        json_dict = [{'text': k, 'children': [{'text': annotation} for annotation in v]} for k, v in
                     unique_annotation_dict.items()]

        return flask.render_template('network_visualization.html', filter_json=json_dict, network_id=network_id)

    @app.route('/network/<int:network_id>', methods=['GET'])
    def get_network_by_id_filtered(network_id):

        graph = process_request(network_id, flask.request.args)

        serve_format = flask.request.args.get('format')

        if serve_format is None:
            return flask.jsonify(to_json_dict(graph))

        if serve_format == 'cx':
            return flask.jsonify(to_cx_json(graph))

        if serve_format == 'bytes':
            g_bytes = to_bytes(graph)
            return flask.Response(g_bytes, mimetype='application/octet-stream')

        if serve_format == 'bel':
            return flask.Response('\n'.join(to_bel_lines(graph)), mimetype='text/plain')

        if serve_format == 'graphml':
            bio = BytesIO()
            to_graphml(graph, bio)
            bio.seek(0)
            s = bio.read().decode('utf-8')
            return flask.Response(s, mimetype='text/xml')

        if serve_format == 'csv':
            sio = StringIO()
            to_csv(graph, sio)
            sio.seek(0)
            return flask.send_file(sio, attachment_filename="testing.txt", as_attachment=True)

        return flask.abort(404)

    @app.route('/supernetwork/', methods=['GET'])
    def get_network_filtered():
        expand_nodes = [api.nid_node[int(h)] for h in flask.request.args.getlist(APPEND_PARAM)]
        remove_nodes = [api.nid_node[int(h)] for h in flask.request.args.getlist(REMOVE_PARAM)]
        annotations = {k: flask.request.args.getlist(k) for k in flask.request.args if
                       k not in BLACK_LIST}

        graph = api.query_all_builder(expand_nodes, remove_nodes, **annotations)

        graph_json = to_json_dict(graph)

        return flask.jsonify(graph_json)

    @app.route('/edges/<int:network_id>/<int:node_id>')
    def get_edges(network_id, node_id):
        res = api.get_incident_edges(network_id, node_id)
        return flask.jsonify(res)

    @app.route('/paths/<int:network_id>', methods=['GET'])
    def get_shortest_path(network_id):
        graph = process_request(network_id, flask.request.args)
        source = flask.request.args.get(SOURCE_NODE)
        target = flask.request.args.get(TARGET_NODE)

        try:
            shortest_path = nx.shortest_path(graph, source=source,
                                             target=target)
        except nx.NetworkXNoPath:
            log.debug('No shortest path between: {} and {}'.format(source, target))
            return []

        return shortest_path

    @app.route('/paths/<int:network_id>', methods=['GET'])
    def get_all_path(network_id):
        graph = process_request(network_id, flask.request.args)
        source = flask.request.args.get(SOURCE_NODE)
        target = flask.request.args.get(TARGET_NODE)

        # TODO: set a 'good' cutoff
        all_paths = nx.all_simple_paths(graph, source=source,
                                        target=target, cutoff=15)

        return all_paths

    @app.route('/nid/')
    def get_node_hashes():
        return flask.jsonify(api.nid_node)

    @app.route('/nid/<nid>')
    def get_node_hash(nid):
        return api.get_node_by_id(nid)

    @app.route('/reload')
    def reload():
        api.load_networks()


def get_app():
    return Flask(__name__)
