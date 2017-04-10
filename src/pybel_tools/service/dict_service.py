# -*- coding: utf-8 -*-

"""This module runs the dictionary-backed PyBEL API"""

import logging
from operator import itemgetter

import flask
import networkx as nx
from flask import Flask, request, jsonify, render_template
from flask_bootstrap import Bootstrap

from pybel.constants import METADATA_DESCRIPTION
from .dict_service_utils import DictionaryService
from .forms import SeedProvenanceForm, SeedSubgraphForm
from .send_utils import serve_network
from ..mutation.metadata import fix_pubmed_citations
from ..selection.induce_subgraph import SEED_TYPES, SEED_TYPE_PROVENANCE
from ..summary import get_annotation_values_by_annotation
from ..summary import get_authors, get_pmids
from ..summary import info_json
from ..web.utils import get_cache_manager

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
PATHS_METHOD = 'paths_method'

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
    SEED_DATA_NODES,
    PATHS_METHOD
}


def sanitize_list_of_str(l):
    """
    :type l: list[str]
    :rtype: list[str]
    """
    return [e for e in (e.strip() for e in l) if e]


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

    return flask.abort(404)


def render_network(graph, network_id=None):
    """Renders the visualization of a network"""
    name = graph.name or DEFAULT_TITLE
    annotations = get_annotation_values_by_annotation(graph)
    json_dict = [{'text': k, 'children': [{'text': annotation} for annotation in sorted(v)]} for k, v in
                 annotations.items()]
    return flask.render_template(
        'explorer.html',
        filter_json=json_dict,
        network_id=network_id if network_id is not None else "0",
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


def build_dictionary_service(app, preload=True, check_version=True):
    """Builds the PyBEL Dictionary-Backed API Service. Adds a latent PyBEL Dictionary service that can be retrieved
    with :func:`get_dict_service`

    :param app: A Flask App
    :type app: Flask
    :param connection: The database connection string. Default location described in
                       :class:`pybel.manager.cache.BaseCacheManager`
    :type connection: str
    """

    manager = get_cache_manager(app)

    api = DictionaryService(manager=manager)

    if preload:
        api.load_networks(check_version=check_version)
        api.load_super_network()

    set_dict_service(app, api)

    def get_graph_from_request(network_id=None):
        """Process the GET request returning the filtered graph
        
        :param network_id: The database id of a network. If none, uses the entire network database, merged.
        :type network_id: int
        :return: A BEL graph
        :rtype: pybel.BELGraph
        """
        network_id = request.args.get(GRAPH_ID, network_id)

        if network_id == 0:
            network_id = None

        seed_method = request.args.get(SEED_TYPE)
        if seed_method is not None and seed_method not in SEED_TYPES:
            raise ValueError('Invalid seed method: {}'.format(seed_method))

        if seed_method and seed_method == SEED_TYPE_PROVENANCE:
            seed_data = {}

            authors = request.args.get(SEED_DATA_AUTHORS)
            if authors:
                seed_data['authors'] = sanitize_list_of_str(authors.split('|'))

            pmids = request.args.get(SEED_DATA_PMIDS)
            if pmids:
                seed_data['pmids'] = sanitize_list_of_str(pmids.split(','))
        elif seed_method:
            seed_data = request.args.get(SEED_DATA_NODES).split(',')
            seed_data = [api.get_node_by_id(h) for h in seed_data]
        else:
            seed_data = None

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

    # Web Pages

    @app.route('/networks/', methods=['GET', 'POST'])
    def view_networks():
        """Renders a page for the user to choose a network"""
        seed_subgraph_form = SeedSubgraphForm()
        seed_provenance_form = SeedProvenanceForm()

        if seed_subgraph_form.validate_on_submit() and seed_subgraph_form.submit_subgraph.data:
            nodes = sanitize_list_of_str(seed_subgraph_form.node_list.data.split(','))
            seed_method = seed_subgraph_form.seed_method.data
            log.info('got subgraph seed: %s', dict(nodes=nodes, method=seed_method))
            # return render_network(api.query(seed_method=seed_method, seed_data=list(nodes)))

        elif seed_provenance_form.validate_on_submit() and seed_provenance_form.submit_provenance.data:
            authors = sanitize_list_of_str(seed_provenance_form.author_list.data.split(','))
            pmids = sanitize_list_of_str(seed_provenance_form.pubmed_list.data.split(','))
            log.info('got prov: %s', dict(authors=authors, pmids=pmids))
            # return render_network(api.query(seed_method=SEED_TYPE_PROVENANCE, seed_data=dict(pmids=pmids, authors=authors)))

        data = [(nid, n.name, n.version, n.document[METADATA_DESCRIPTION]) for nid, n in api.networks.items()]

        return flask.render_template(
            'network_list.html',
            data=data,
            provenance_form=seed_provenance_form,
            subgraph_form=seed_subgraph_form
        )

    @app.route('/explore/', methods=['GET'])
    @app.route('/explore/<int:network_id>', methods=['GET'])
    def view_explorer(network_id=None):
        """Renders a page for the user to explore a network"""
        if network_id == 0:
            network_id = None

        graph = get_graph_from_request(network_id=network_id)
        return render_network(graph, network_id)

    @app.route('/definitions')
    def view_definitions():
        """Displays a page listing the namespaces and annotations."""
        return render_template('definitions_list.html', namespaces=api.list_namespaces(),
                               annotations=api.list_annotations())

    # App Control

    @app.route('/admin/reload')
    def run_reload():
        api.load_networks()
        api.get_super_network(reload=True)
        return jsonify({'status': 200})

    @app.route('/admin/enrich')
    def run_enrich_authors():
        """Enriches information in network. Be patient"""
        fix_pubmed_citations(api.full_network)
        return jsonify({'status': 200})

    # Data Service
    @app.route('/api/network/', methods=['GET'])
    @app.route('/api/network/<int:network_id>', methods=['GET'])
    def get_network(network_id=None):
        """Builds a graph from the given network id and sends it in the given format"""
        graph = get_graph_from_request(network_id=network_id)
        return serve_network(graph, request.args.get(FORMAT))

    @app.route('/api/edges/incident/<int:network_id>/<int:node_id>')
    def get_incident_edges(network_id, node_id):
        res = api.get_incident_edges(network_id, node_id)
        return jsonify(res)

    @app.route('/api/paths')
    @app.route('/api/paths/<int:network_id>', methods=['GET'])
    def get_shortest_path(network_id=None):
        graph = get_graph_from_request(network_id=network_id)

        if SOURCE_NODE not in request.args:
            raise ValueError('no source')

        if TARGET_NODE not in request.args:
            raise ValueError('no target')

        method = request.args.get(PATHS_METHOD)
        source = request.args.get(SOURCE_NODE)
        target = request.args.get(TARGET_NODE)

        source = int(source)
        target = int(target)


        undirected = UNDIRECTED in request.args

        log.info('Source: %s, target: %s', source, target)

        if source not in graph or target not in graph:
            log.info('Source/target node not in graph')
            log.info('Nodes in graph: %s', graph.nodes())
            return flask.abort(500)

        if undirected:
            graph = graph.to_undirected()

        if method == 'all':
            all_paths = nx.all_simple_paths(graph, source=source, target=target, cutoff=7)
            # all_paths is a generator -> convert to list and create a list of lists (paths)
            return jsonify([path for path in list(all_paths)])

        try:
            shortest_path = nx.shortest_path(graph, source=source, target=target)
        except nx.NetworkXNoPath:
            log.debug('No paths between: {} and {}'.format(source, target))
            return 'No paths between the selected nodes'

        return jsonify(shortest_path)

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

    @app.route('/api/authors')
    def get_all_authors():
        graph = get_graph_from_request()
        return jsonify(sorted(get_authors(graph)))

    @app.route('/api/pmids')
    def get_all_pmids():
        graph = get_graph_from_request()
        return jsonify(sorted(get_pmids(graph)))

    @app.route('/api/nodes/')
    def get_node_hashes():
        return jsonify(api.nid_node)

    @app.route('/api/nodes/<nid>')
    def get_node_hash(nid):
        return jsonify(api.get_node_by_id(nid))

    @app.route('/api/summary/<int:network_id>')
    def get_number_nodes(network_id):
        return jsonify(info_json(api.get_network_by_id(network_id)))

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

    @app.route('/api/edges/provenance/<int:sid>/<int:tid>')
    def get_edges(sid, tid):
        return jsonify(api.get_edges(api.get_node_by_id(sid), api.get_node_by_id(tid)))

    log.info('Added dictionary service to %s', app)


def get_app():
    app = Flask(__name__)
    Bootstrap(app)
    return app
