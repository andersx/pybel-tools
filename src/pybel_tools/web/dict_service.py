# -*- coding: utf-8 -*-

"""This module runs the dictionary-backed PyBEL API"""

import logging
from operator import itemgetter

import flask
import networkx as nx
from flask import Flask, request, jsonify, url_for, redirect
from flask import render_template
from flask_basicauth import BasicAuth
from requests.compat import unquote

from pybel import from_bytes
from pybel import from_url
from pybel.constants import SMALL_CORPUS_URL, LARGE_CORPUS_URL, FRAUNHOFER_RESOURCES
from .dict_service_utils import DictionaryService
from .forms import SeedProvenanceForm, SeedSubgraphForm
from .send_utils import serve_network
from .utils import try_insert_graph, sanitize_list_of_str
from ..mutation.metadata import fix_pubmed_citations
from ..selection.induce_subgraph import SEED_TYPES, SEED_TYPE_PROVENANCE
from ..summary.edge_summary import count_relations
from ..summary.edge_summary import get_annotation_values_by_annotation
from ..summary.error_summary import count_error_types
from ..summary.export import info_json
from ..summary.node_properties import get_translocated, get_activities, get_degradations, count_variants
from ..summary.node_summary import count_functions, count_namespaces
from ..summary.provenance import get_authors, get_pmids
from ..utils import prepare_c3

log = logging.getLogger(__name__)

DICTIONARY_SERVICE = 'dictionary_service'
DEFAULT_TITLE = 'Biological Network Explorer'
TAB_DELIMITER = '|'
COMMA_DELIMITER = ','

APPEND_PARAM = 'append'
REMOVE_PARAM = 'remove'
SOURCE_NODE = 'source'
TARGET_NODE = 'target'
FORMAT = 'format'
UNDIRECTED = 'undirected'
NODE_NUMBER = 'node_number'
GRAPH_ID = 'graphid'
SEED_TYPE = 'seed_method'
SEED_DATA_AUTHORS = 'authors'
SEED_DATA_PMIDS = 'pmids'
SEED_DATA_NODES = 'nodes'
PATHS_METHOD = 'paths_method'
PIPELINE = 'pipeline'

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
    PATHS_METHOD,
    PIPELINE,
}


def get_tree_annotations(graph):
    """ Builds tree structure with annotation for a given graph
    
    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :return: The JSON structure necessary for building the tree box
    :rtype: list[dict]
    """
    annotations = get_annotation_values_by_annotation(graph)
    return [{'text': annotation, 'children': [{'text': value} for value in sorted(values)]} for annotation, values in
            sorted(annotations.items())]


def build_dictionary_service(app, manager, preload=True, check_version=True, admin_password=None,
                             analysis_enabled=False):
    """Builds the PyBEL Dictionary-Backed API Service. Adds a latent PyBEL Dictionary service that can be retrieved
    with :func:`get_dict_service`

    :param app: A Flask App
    :type app: Flask
    :param manager: A PyBEL cache manager
    :type manager: pybel.manager.cache.CacheManager
    :param preload: Should the networks be preloaded?
    :type preload: bool
    :param check_version: Should the versions of the networks be checked during loading?
    :type check_version: bool
    :param admin_password: The administrator password for accessing restricted web pages
    :type admin_password: str
    """
    api = DictionaryService(manager=manager)

    if preload:
        log.info('loading networks')
        api.load_networks(check_version=check_version)
        log.info('pre-loaded the dict service')

    if admin_password is not None:
        app.config['BASIC_AUTH_USERNAME'] = 'pybel'
        app.config['BASIC_AUTH_PASSWORD'] = admin_password

        basic_auth = BasicAuth(app)

        @app.route('/admin/reload')
        @basic_auth.required
        def run_reload():
            """Reloads the networks and supernetwork"""
            api.load_networks(force_reload=True)
            return jsonify({'status': 200})

        @app.route('/admin/enrich')
        @basic_auth.required
        def run_enrich_authors():
            """Enriches information in network. Be patient"""
            fix_pubmed_citations(api.universe)
            return jsonify({'status': 200})

        @app.route('/admin/rollback')
        @basic_auth.required
        def rollback():
            """Rolls back the transaction for when something bad happens"""
            manager.rollback()
            return jsonify({'status': 200})

        @app.route('/admin/ensure/small')
        @basic_auth.required
        def ensure_small_corpus():
            """Parses the small corpus"""
            graph = from_url(SMALL_CORPUS_URL, manager=manager, citation_clearing=False, allow_nested=True)
            return try_insert_graph(manager, graph, api)

        @app.route('/admin/ensure/large')
        @basic_auth.required
        def ensure_large_corpus():
            """Parses the large corpus"""
            graph = from_url(LARGE_CORPUS_URL, manager=manager, citation_clearing=False, allow_nested=True)
            return try_insert_graph(manager, graph, api)

        @app.route('/admin/ensure/abstract3')
        @basic_auth.required
        def ensure_abstract3():
            """Ensures Selventa Example 3"""
            url = 'http://resources.openbel.org/belframework/20150611/knowledge/full_abstract3.bel'
            graph = from_url(url, manager=manager, citation_clearing=False, allow_nested=True)
            return try_insert_graph(manager, graph, api)

        @app.route('/admin/ensure/gfam')
        @basic_auth.required
        def ensure_gfam():
            graph = from_url(FRAUNHOFER_RESOURCES + 'gfam_members.bel', manager=manager)
            return try_insert_graph(manager, graph, api)

        @app.route('/admin/drop/all')
        @basic_auth.required
        def nuke():
            """Destroys the database and recreates it"""
            log.info('nuking database')
            manager.drop_database()
            manager.create_database()
            log.info('restarting dictionary service')
            api.load_networks(force_reload=True)
            log.info('... the dust settles')
            return jsonify({'status': 200})

        @app.route('/admin/drop/graphs')
        @basic_auth.required
        def drop_graphs():
            """Drops all graphs"""
            log.info('dropping all graphs')
            manager.drop_graphs()
            return jsonify({'status': 200})

        log.info('added admin functions to dict service')

    def get_graph_from_request():
        """Process the GET request returning the filtered graph
        :return: graph: A BEL graph
        :rtype: pybel.BELGraph
        """

        network_id = request.args.get(GRAPH_ID)

        if network_id is not None:
            network_id = int(network_id)

        if network_id == 0:
            network_id = None

        seed_method = request.args.get(SEED_TYPE)
        if seed_method and seed_method not in SEED_TYPES:
            raise ValueError('Invalid seed method: {}'.format(seed_method))

        if seed_method and seed_method == SEED_TYPE_PROVENANCE:
            seed_data = {}

            authors = request.args.getlist(SEED_DATA_AUTHORS)

            if authors:
                seed_data['authors'] = [unquote(author) for author in authors]

            pmids = request.args.getlist(SEED_DATA_PMIDS)
            if pmids:
                seed_data['pmids'] = pmids
        elif seed_method:
            seed_data = request.args.getlist(SEED_DATA_NODES)
            seed_data = [api.decode_node(h) for h in seed_data]
        else:
            seed_data = None

        expand_nodes = request.args.get(APPEND_PARAM)
        remove_nodes = request.args.get(REMOVE_PARAM)

        if expand_nodes:
            expand_nodes = [api.decode_node(h) for h in expand_nodes.split(',')]

        if remove_nodes:
            remove_nodes = [api.decode_node(h) for h in remove_nodes.split(',')]

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
            # nodes = sanitize_list_of_str()
            seed_data_nodes = seed_subgraph_form.node_list.data.split('|')
            seed_method = seed_subgraph_form.seed_method.data
            log.info('got subgraph seed: %s', dict(nodes=seed_data_nodes, method=seed_method))
            url = url_for('view_explorer', **{
                GRAPH_ID: '0',
                SEED_TYPE: seed_method,
                SEED_DATA_NODES: seed_data_nodes,
                'autoload': 'yes',
            })
            log.info('redirecting to %s', url)
            return redirect(url)
        elif seed_provenance_form.validate_on_submit() and seed_provenance_form.submit_provenance.data:
            authors = sanitize_list_of_str(seed_provenance_form.author_list.data.split(','))
            pmids = sanitize_list_of_str(seed_provenance_form.pubmed_list.data.split(','))
            log.info('got prov: %s', dict(authors=authors, pmids=pmids))
            url = url_for('view_explorer', **{
                GRAPH_ID: '0',
                SEED_TYPE: SEED_TYPE_PROVENANCE,
                SEED_DATA_PMIDS: pmids,
                SEED_DATA_AUTHORS: authors,
                'autoload': 'yes',
            })
            log.info('redirecting to %s', url)
            return redirect(url)

        return flask.render_template(
            'network_list.html',
            data=manager.list_graphs(),
            provenance_form=seed_provenance_form,
            subgraph_form=seed_subgraph_form,
            analysis_enabled=analysis_enabled
        )

    @app.route('/explore/', methods=['GET'])
    def view_explorer():
        """Renders a page for the user to explore a network"""
        return flask.render_template('explorer.html')

    @app.route('/summary/<int:graph_id>')
    def view_summary(graph_id):
        """Renders a page with the parsing errors for a given BEL script"""
        graph = manager.get_graph_by_id(graph_id)
        graph = from_bytes(graph.blob)

        return render_template(
            'summary.html',
            chart_1_data=prepare_c3(count_functions(graph), 'Entity Type'),
            chart_2_data=prepare_c3(count_relations(graph), 'Relationship Type'),
            chart_3_data=prepare_c3(count_error_types(graph), 'Error Type'),
            chart_4_data=prepare_c3({
                'Translocations': len(get_translocated(graph)),
                'Degradations': len(get_degradations(graph)),
                'Molecular Activities': len(get_activities(graph))
            }, 'Modifier Type'),
            chart_5_data=prepare_c3(count_variants(graph), 'Node Variants'),
            chart_6_data=prepare_c3(count_namespaces(graph), 'Namespaces'),
            chart_7_data=prepare_c3(api.get_top_degree(graph_id), 'Top Hubs'),
            chart_8_data=prepare_c3(api.get_top_centrality(graph_id), 'Top Central'),
            chart_9_data=prepare_c3(api.get_top_comorbidities(graph_id), 'Diseases'),
            graph=graph,
            time=None,
        )

    @app.route('/definitions')
    def view_definitions():
        """Displays a page listing the namespaces and annotations."""
        return render_template('definitions_list.html', namespaces=sorted(manager.list_namespaces()),
                               annotations=sorted(manager.list_annotations()))

    # Data Service

    @app.route('/api/network/list', methods=['GET'])
    def get_network_list():
        return jsonify(manager.list_graphs())

    @app.route('/api/summary/<int:network_id>')
    def get_number_nodes(network_id):
        """Gets a summary of the given network"""
        return jsonify(info_json(api.get_network(network_id)))

    @app.route('/api/network/', methods=['GET'])
    def get_network():
        """Builds a graph from the given network id and sends it in the given format"""
        graph = get_graph_from_request()
        return serve_network(graph, request.args.get(FORMAT))

    @app.route('/api/tree/')
    def get_tree_api():
        """Builds the annotation tree data structure for a given graph"""
        graph = get_graph_from_request()
        return jsonify(get_tree_annotations(graph))

    @app.route('/api/paths/')
    def get_paths_api():
        """Returns array of shortest/all paths given a source node and target node both belonging in the graph
        :return: JSON 
        """
        graph = get_graph_from_request()

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
            return jsonify(list(all_paths))

        try:
            shortest_path = nx.shortest_path(graph, source=source, target=target)
        except nx.NetworkXNoPath:
            log.debug('No paths between: {} and {}'.format(source, target))
            return 'No paths between the selected nodes'

        return jsonify(shortest_path)

    @app.route('/api/centrality/', methods=['GET'])
    def get_nodes_by_betweenness_centrality():
        """Gets a list of nodes with the top betweenness-centrality"""
        graph = get_graph_from_request()

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
        """Gets a list of all authors in the graph produced by the given URL parameters"""
        graph = get_graph_from_request()
        return jsonify(sorted(get_authors(graph)))

    @app.route('/api/pmids')
    def get_all_pmids():
        """Gets a list of all pubmed citation identifiers in the graph produced by the given URL parameters"""
        graph = get_graph_from_request()
        return jsonify(sorted(get_pmids(graph)))

    @app.route('/api/nodes/')
    def get_node_hashes():
        """Gets the dictionary of {node id: pybel node tuples}"""
        return jsonify(api.nid_node)

    @app.route('/api/nodes/<nid>')
    def get_node_hash(nid):
        """Gets the pybel node tuple"""
        return jsonify(api.get_node_by_id(nid))

    @app.route('/api/suggestion/nodes/')
    def get_node_suggestion():
        """Suggests a node based on the search criteria"""
        if not request.args['search']:
            return jsonify([])

        autocompletion_set = api.get_nodes_containing_keyword(request.args['search'])

        return jsonify(autocompletion_set)

    @app.route('/api/suggestion/authors/')
    def get_author_suggestion():
        """Return list of authors matching the author keyword"""

        autocompletion_set = api.get_authors_containing_keyword(request.args['search'])

        return jsonify([{"text": pubmed, "id": index} for index, pubmed in enumerate(autocompletion_set)])

    @app.route('/api/suggestion/pubmed/')
    def get_pubmed_suggestion():
        """Return list of pubmedids matching the integer keyword"""

        autocompletion_set = api.get_pubmed_containing_keyword(request.args['search'])

        return jsonify([{"text": pubmed, "id": index} for index, pubmed in enumerate(autocompletion_set)])

    @app.route('/api/edges/provenance/<int:sid>/<int:tid>')
    def get_edges(sid, tid):
        """Gets all edges between the two given nodes"""
        return jsonify(api.get_edges(api.decode_node(sid), api.decode_node(tid)))

    @app.route('/api/meta/blacklist')
    def get_blacklist():
        """Return list of blacklist constants"""
        return jsonify(sorted(BLACK_LIST))

    log.info('Added dictionary service to %s', app)
