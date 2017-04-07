# -*- coding: utf-8 -*-

"""This module runs the dictionary-backed PyBEL API"""

import logging
from operator import itemgetter

import flask
import networkx as nx
from flask import Flask

from pybel import to_cx_json, to_graphml, to_bytes, to_bel_lines, to_json_dict, to_csv
from .dict_service_utils import DictionaryService
from ..summary import get_annotation_values_by_annotation

try:
    from StringIO import StringIO
    from BytesIO import BytesIO
except ImportError:
    from io import StringIO, BytesIO

log = logging.getLogger(__name__)

DICTIONARY_SERVICE = 'dictionary_service'
DEFAULT_TITLE = 'Biological Network Explorer'

APPEND_PARAM = 'append'
REMOVE_PARAM = 'remove'
SOURCE_NODE = 'source'
TARGET_NODE = 'target'
FORMAT = 'format'
UNDIRECTED = 'undirected'
NODE_NUMBER = 'node_number'
NODE_LIST = 'node_list'
PUBMED_IDS = 'pubmed_list'
AUTHORS = 'author_list'
SUPER_NETWORK = 'supernetwork'
ANALYSIS_TYPE = 'analysis'
ANALYSIS_TYPE_SUBGRAPH = 'induce_subgraph'
ANALYSIS_TYPE_EXPAND = 'expand_neighbors'
ANALYSIS_TYPE_PATHS = 'shortest_paths'

BLACK_LIST = {
    APPEND_PARAM,
    REMOVE_PARAM,
    SOURCE_NODE,
    TARGET_NODE,
    UNDIRECTED,
    NODE_NUMBER,
    FORMAT,
    ANALYSIS_TYPE,
}


def raise_invalid_source_target():
    if SOURCE_NODE not in flask.request.args:
        raise ValueError('Not source node in request')
    if TARGET_NODE not in flask.request.args:
        raise ValueError('Not taget node in request')
    try:
        int(flask.request.args.get(SOURCE_NODE))
    except ValueError:
        raise ValueError('{} is not valid node'.format(flask.request.args.get(SOURCE_NODE)))
    try:
        int(flask.request.args.get(TARGET_NODE))
    except ValueError:
        raise ValueError('{} is not valid node'.format(flask.request.args.get(TARGET_NODE)))


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


def build_dictionary_service_app(app, connection=None):
    """Builds the PyBEL Dictionary-Backed API Service. Adds a latent PyBEL Dictionary service that can be retrieved
    with :func:`get_dict_service`

    :param app: A Flask App
    :type app: Flask
    :param connection: The database connection string. Default location described in
                       :code:`pybel.manager.cache.BaseCacheManager`
    :type connection: str
    """
    api = DictionaryService(connection=connection)
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
            expand_nodes = [api.get_node_by_id(h) for h in expand_nodes.split(',')]

        if remove_nodes:
            remove_nodes = [api.get_node_by_id(h) for h in remove_nodes.split(',')]

        annotations = {k: args.getlist(k) for k in args if k not in BLACK_LIST}

        graph = api.query_filtered_builder(network_id, expand_nodes, remove_nodes, **annotations)

        return graph

    @app.route('/')
    def list_networks():
        data = [(nid, n.name, n.version) for nid, n in api.networks.items()]
        return flask.render_template('network_list.html', data=data)

    @app.route('/network/filter/<int:network_id>', methods=['GET'])
    def get_filter(network_id):
        graph = api.get_network_by_id(network_id)
        name = graph.name or DEFAULT_TITLE

        unique_annotation_dict = get_annotation_values_by_annotation(graph)

        json_dict = [{'text': k, 'children': [{'text': annotation} for annotation in v]} for k, v in
                     unique_annotation_dict.items()]

        return flask.render_template('network_visualization.html',
                                     filter_json=json_dict,
                                     network_id=network_id,
                                     network_name=name)

    @app.route('/network/<int:network_id>', methods=['GET'])
    def get_network_by_id_filtered(network_id):

        graph = process_request(network_id, flask.request.args)

        serve_format = flask.request.args.get(FORMAT)

        if serve_format is None:
            data = to_json_dict(graph)
            return flask.jsonify(data)

        if serve_format == 'cx':
            data = to_cx_json(graph)
            return flask.jsonify(data)

        if serve_format == 'bytes':
            data = to_bytes(graph)
            return flask.send_file(data, mimetype='application/octet-stream', as_attachment=True,
                                   attachment_filename='graph.gpickle')

        if serve_format == 'bel':
            data = '\n'.join(to_bel_lines(graph))
            return flask.Response(data, mimetype='text/plain')

        if serve_format == 'graphml':
            bio = BytesIO()
            to_graphml(graph, bio)
            bio.seek(0)
            data = StringIO(bio.read().decode('utf-8'))
            return flask.send_file(data, mimetype='text/xml', attachment_filename='graph.graphml', as_attachment=True)

        if serve_format == 'csv':
            bio = BytesIO()
            to_csv(graph, bio)
            bio.seek(0)
            data = StringIO(bio.read().decode('utf-8'))
            return flask.send_file(data, attachment_filename="graph.tsv", as_attachment=True)

        return flask.abort(404)

    @app.route('/supernetwork/', methods=['GET'])
    def get_network_filtered():
        expand_nodes = [api.get_node_by_id(h) for h in flask.request.args.getlist(APPEND_PARAM)]
        remove_nodes = [api.get_node_by_id(h) for h in flask.request.args.getlist(REMOVE_PARAM)]
        annotations = {k: flask.request.args.getlist(k) for k in flask.request.args if
                       k not in BLACK_LIST}

        graph = api.query_all_builder(expand_nodes, remove_nodes, **annotations)

        graph_json = to_json_dict(graph)

        return flask.jsonify(graph_json)

    @app.route('/edges/<int:network_id>/<int:node_id>')
    def get_incident_edges(network_id, node_id):
        res = api.get_incident_edges(network_id, node_id)
        return flask.jsonify(res)

    @app.route('/paths/shortest/<int:network_id>', methods=['GET'])
    def get_shortest_path(network_id):
        graph = process_request(network_id, flask.request.args)

        try:
            raise_invalid_source_target()
        except ValueError as e:
            return str(e)

        source = int(flask.request.args.get(SOURCE_NODE))
        target = int(flask.request.args.get(TARGET_NODE))

        undirected = UNDIRECTED in flask.request.args

        log.info('Source: %s, target: %s', source, target)

        if source not in graph or target not in graph:
            log.info('Source/target node not in graph')
            log.info('Nodes in graph: %s', graph.nodes())
            return flask.abort(500)

        if undirected:
            graph = graph.to_undirected()

        try:
            shortest_path = nx.shortest_path(graph, source=source, target=target)
        except nx.NetworkXNoPath:
            log.debug('No paths between: {} and {}'.format(source, target))
            return 'No paths between the selected nodes'

        return flask.jsonify(shortest_path)

    @app.route('/paths/all/<int:network_id>', methods=['GET'])
    def get_all_path(network_id):
        graph = process_request(network_id, flask.request.args)

        try:
            raise_invalid_source_target()
        except ValueError as e:
            return str(e)

        source = int(flask.request.args.get(SOURCE_NODE))
        target = int(flask.request.args.get(TARGET_NODE))

        undirected = UNDIRECTED in flask.request.args

        if source not in graph or target not in graph:
            log.info('Source/target node not in graph')
            log.info('Nodes in graph: %s', graph.nodes())
            return flask.abort(500)

        if undirected:
            graph = graph.to_undirected()

        all_paths = nx.all_simple_paths(graph, source=source, target=target, cutoff=7)

        # all_paths is a generator -> convert to list and create a list of lists (paths)
        return flask.jsonify([path for path in list(all_paths)])

    @app.route('/centrality/<int:network_id>', methods=['GET'])
    def get_nodes_by_betweenness_centrality(network_id):
        graph = process_request(network_id, flask.request.args)

        try:
            node_numbers = int(flask.request.args.get(NODE_NUMBER))

        except ValueError:
            return 'Please enter a number'

        if node_numbers > nx.number_of_nodes(graph):
            return 'The number introduced is bigger than the nodes in the network'

        bw_dict = nx.betweenness_centrality(graph)

        node_list = [i[0] for i in sorted(bw_dict.items(), key=itemgetter(1), reverse=True)[0:node_numbers]]

        return flask.jsonify(node_list)

    @app.route('/nid/')
    def get_node_hashes():
        return flask.jsonify(api.nid_node)

    @app.route('/nid/<nid>')
    def get_node_hash(nid):
        return api.get_node_by_id(nid)

    @app.route('/api/nodes/suggestion/<node>')
    def get_node_suggestion(node):

        keywords = [entry.strip() for entry in node.split(',')]

        autocompletion_set = api.get_nodes_containing_keyword(keywords[-1])

        return flask.jsonify(list(autocompletion_set))

    @app.route('/api/edges/<int:sid>/<int:tid>')
    def get_edges(sid, tid):
        return flask.jsonify(api.get_edges(api.get_node_by_id(sid), api.get_node_by_id(tid)))

    @app.route('/reload')
    def reload():
        api.load_networks()
        api.get_super_network(force=True)
        return flask.jsonify({'status': 200})


def get_app():
    return Flask(__name__)
