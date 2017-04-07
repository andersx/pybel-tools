# -*- coding: utf-8 -*-

"""This module runs the dictionary-backed PyBEL API"""

import logging
from operator import itemgetter

import flask
import networkx as nx
from flask import Flask, request, jsonify

from pybel import to_cx_json, to_graphml, to_bytes, to_bel_lines, to_json_dict, to_csv
from .dict_service_utils import DictionaryService
from ..selection.induce_subgraph import SEED_TYPES, SEED_TYPE_PROVENANCE
from ..summary import get_annotation_values_by_annotation

try:
    from StringIO import StringIO
    from BytesIO import BytesIO
except ImportError:
    from io import StringIO, BytesIO

log = logging.getLogger(__name__)

DICTIONARY_SERVICE = 'dictionary_service'
DEFAULT_TITLE = 'Biological Network Explorer'
DELIMITER = '|'

APPEND_PARAM = 'append'
REMOVE_PARAM = 'remove'
SOURCE_NODE = 'source'
TARGET_NODE = 'target'
FORMAT = 'format'
UNDIRECTED = 'undirected'
NODE_NUMBER = 'node_number'
GRAPH_ID = 'graphid'
SEED_TYPE = 'analysis'
SEED_DATA_AUTHORS = 'authors'
SEED_DATA_PMIDS = 'pmids'
SEED_DATA_NODES = 'nodes'

BLACK_LIST = {
    GRAPH_ID,
    APPEND_PARAM,
    REMOVE_PARAM,
    SOURCE_NODE,
    TARGET_NODE,
    UNDIRECTED,
    NODE_NUMBER,
    FORMAT,
    SEED_TYPE,
    SEED_DATA_AUTHORS,
    SEED_DATA_PMIDS,
    SEED_DATA_NODES
}


def raise_invalid_source_target():
    if SOURCE_NODE not in request.args:
        raise ValueError('Not source node in request')
    if TARGET_NODE not in request.args:
        raise ValueError('Not taget node in request')
    try:
        int(request.args.get(SOURCE_NODE))
    except ValueError:
        raise ValueError('{} is not valid node'.format(request.args.get(SOURCE_NODE)))
    try:
        int(request.args.get(TARGET_NODE))
    except ValueError:
        raise ValueError('{} is not valid node'.format(request.args.get(TARGET_NODE)))


def serve_network(graph):
    """A helper function to serialize a graph and download as a file"""
    serve_format = request.args.get(FORMAT)

    if serve_format is None or serve_format == 'json':
        data = to_json_dict(graph)
        return jsonify(data)

    if serve_format == 'cx':
        data = to_cx_json(graph)
        return jsonify(data)

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

def render_network(graph, network_id):
    name = graph.name or DEFAULT_TITLE

    unique_annotation_dict = get_annotation_values_by_annotation(graph)

    json_dict = [{'text': k, 'children': [{'text': annotation} for annotation in v]} for k, v in unique_annotation_dict.items()]

    return flask.render_template(
        'network_visualization.html',
        filter_json=json_dict,
        network_id=network_id,
        network_name=name
    )

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

    def get_graph_from_request(network_id=None):
        """Process the GET request returning the filtered graph
        
        :param network_id: The database id of a network. If none, uses the entire network database, merged.
        :type network_id: int
        :return: A BEL graph
        :rtype: pybel.BELGraph
        """
        # Convert from list of hashes (as integers) to node tuples
        network_id = request.args.get(GRAPH_ID, network_id)

        seed_method = request.args.get(SEED_TYPE)
        if seed_method is not None and seed_method not in SEED_TYPES:
            raise ValueError('Invalid seed method: {}'.format(seed_method))

        if seed_method == SEED_TYPE_PROVENANCE:
            seed_data = {}

            authors = request.args.get(SEED_DATA_AUTHORS)
            if authors:
                seed_data['authors'] = authors.split('|')

            pmids = request.args.get(SEED_DATA_PMIDS)
            if pmids:
                seed_data['pmids'] = pmids.split(',')
        else:
            seed_data = request.args.get(SEED_DATA_NODES).split(',')
            seed_data = [api.get_node_by_id(h) for h in seed_data]

        expand_nodes = request.args.get(APPEND_PARAM)
        remove_nodes = request.args.get(REMOVE_PARAM)

        if expand_nodes:
            expand_nodes = [api.get_node_by_id(h) for h in expand_nodes.split(',')]

        if remove_nodes:
            remove_nodes = [api.get_node_by_id(h) for h in remove_nodes.split(',')]

        annotations = {k: request.args.getlist(k) for k in request.args if k not in BLACK_LIST}

        graph = api.query(
            network_id=network_id,
            seed_method=seed_method,
            seed_data=seed_data,
            expand_nodes=expand_nodes,
            remove_nodes=remove_nodes,
            **annotations
        )

        return graph

    @app.route('/')
    def list_networks():
        data = [(nid, n.name, n.version) for nid, n in api.networks.items()]
        return flask.render_template('network_list.html', data=data)

    @app.route('/network/<int:network_id>', methods=['GET'])
    def view_network(network_id):
        """Renders a page for the user to explore a network"""
        if network_id == 0:
            network_id = ''

        graph = api.get_network_by_id(network_id)
        return render_network(graph, network_id)

    @app.route('/network/', methods=['GET'])
    def view_supernetwork():
        """Renders a page for the user to explore a network"""
        graph = api.get_network_by_id()
        return render_network(graph, '')

    @app.route('/api/query/network/', methods=['GET'])
    def ultimate_network_query():
        graph = get_graph_from_request()
        return jsonify(to_json_dict(graph))

    @app.route('/api/network/', methods=['GET'])
    def download_network():
        """Builds a graph and sends it in the given format"""
        graph = get_graph_from_request()
        return serve_network(graph)

    @app.route('/api/network/<int:network_id>', methods=['GET'])
    def download_network_by_id(network_id):
        """Builds a graph from the given network id and sends it in the given format"""
        graph = get_graph_from_request(network_id=network_id)
        return serve_network(graph)

    @app.route('/api/edges/<int:network_id>/<int:node_id>')
    def get_incident_edges(network_id, node_id):
        res = api.get_incident_edges(network_id, node_id)
        return jsonify(res)

    @app.route('/api/paths/shortest/<int:network_id>', methods=['GET'])
    def get_shortest_path(network_id):
        graph = get_graph_from_request(network_id=network_id)

        try:
            raise_invalid_source_target()
        except ValueError as e:
            return str(e)

        source = int(request.args.get(SOURCE_NODE))
        target = int(request.args.get(TARGET_NODE))

        undirected = UNDIRECTED in request.args

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

        return jsonify(shortest_path)

    @app.route('/api/paths/all/<int:network_id>', methods=['GET'])
    def get_all_path(network_id):
        graph = get_graph_from_request(network_id=network_id)

        try:
            raise_invalid_source_target()
        except ValueError as e:
            return str(e)

        source = int(request.args.get(SOURCE_NODE))
        target = int(request.args.get(TARGET_NODE))

        undirected = UNDIRECTED in request.args

        if source not in graph or target not in graph:
            log.info('Source/target node not in graph')
            log.info('Nodes in graph: %s', graph.nodes())
            return flask.abort(500)

        if undirected:
            graph = graph.to_undirected()

        all_paths = nx.all_simple_paths(graph, source=source, target=target, cutoff=7)

        # all_paths is a generator -> convert to list and create a list of lists (paths)
        return jsonify([path for path in list(all_paths)])

    @app.route('/api/centrality/<int:network_id>', methods=['GET'])
    def get_nodes_by_betweenness_centrality(network_id):
        graph = get_graph_from_request(network_id=network_id)

        try:
            node_numbers = int(request.args.get(NODE_NUMBER))
        except ValueError:
            return 'Please enter a number'

        if node_numbers > nx.number_of_nodes(graph):
            return 'The number introduced is bigger than the nodes in the network'

        bw_dict = nx.betweenness_centrality(graph)

        node_list = [i[0] for i in sorted(bw_dict.items(), key=itemgetter(1), reverse=True)[0:node_numbers]]

        return jsonify(node_list)

    @app.route('/api/nid/')
    def get_node_hashes():
        return jsonify(api.nid_node)

    @app.route('/api/nid/<nid>')
    def get_node_hash(nid):
        return jsonify(api.get_node_by_id(nid))

    @app.route('/api/suggestion/nodes/<node>')
    def get_node_suggestion(node):

        keywords = [entry.strip() for entry in node.split(DELIMITER)]

        autocompletion_set = api.get_nodes_containing_keyword(keywords[-1])

        return jsonify(list(autocompletion_set))

    @app.route('/api/suggestion/authors/<author>')
    def get_author_suggestion(author):

        keywords = [entry.strip() for entry in author.split(DELIMITER)]

        autocompletion_set = api.get_authors_containing_keyword(keywords[-1])

        return jsonify(list(autocompletion_set))

    @app.route('/api/suggestion/pubmed/<pubmed>')
    def get_pubmed_suggestion(pubmed):

        keywords = [entry.strip() for entry in pubmed.split(DELIMITER)]

        autocompletion_set = api.get_pubmed_containing_keyword(keywords[-1])

        return jsonify(list(autocompletion_set))

    @app.route('/api/edges/<int:sid>/<int:tid>')
    def get_edges(sid, tid):
        return jsonify(api.get_edges(api.get_node_by_id(sid), api.get_node_by_id(tid)))

    @app.route('/reload')
    def reload():
        api.load_networks()
        api.get_super_network(force=True)
        return jsonify({'status': 200})


def get_app():
    return Flask(__name__)
