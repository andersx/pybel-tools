# -*- coding: utf-8 -*-

"""This module runs the dictionary-backed PyBEL API"""

import logging
import time
from operator import itemgetter

import flask
import networkx as nx
from flask import render_template
from flask import request, jsonify, url_for, redirect, make_response
from flask_security import roles_required, roles_accepted, current_user, login_required
from requests.compat import unquote
from six import StringIO

from pybel import from_bytes
from pybel import from_url
from pybel.constants import *
from pybel.manager.models import Namespace, Annotation, Network
from .dict_service_utils import DictionaryService
from .extension import get_manager, get_api
from .forms import SeedProvenanceForm, SeedSubgraphForm
from .models import Report
from .send_utils import serve_network
from .utils import render_graph_summary
from .utils import try_insert_graph, sanitize_list_of_str
from ..constants import BMS_BASE
from ..definition_utils import write_namespace
from ..ioutils import convert_recursive, upload_recursive, get_paths_recursive
from ..mutation.metadata import fix_pubmed_citations
from ..selection.induce_subgraph import SEED_TYPES, SEED_TYPE_PROVENANCE
from ..summary.edge_summary import get_tree_annotations
from ..summary.error_summary import get_undefined_namespace_names, get_incorrect_names
from ..summary.export import info_json
from ..summary.provenance import get_authors, get_pmids

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
GRAPH_ID = 'graphid'
SEED_TYPE = 'seed_method'
SEED_DATA_AUTHORS = 'authors'
SEED_DATA_PMIDS = 'pmids'
SEED_DATA_NODES = 'nodes'
PATHS_METHOD = 'paths_method'
PIPELINE = 'pipeline'
AUTOLOAD = 'autoload'
FILTERS = 'filters'
# TODO: delete once pipeline is ready
FILTER_PATHOLOGIES = 'pathology_filter'

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
    AUTOLOAD,
    FILTERS,
    FILTER_PATHOLOGIES,
}


def get_graph_from_request(api):
    """Process the GET request returning the filtered graph
    
    :param DictionaryService api: The dictionary service
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
    filters = request.args.getlist(FILTERS)

    filter_pathologies = request.args.get(FILTER_PATHOLOGIES)

    if filter_pathologies and filter_pathologies in {'True', True}:
        filter_pathologies = True

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
        filters=filters,
        filter_pathologies=filter_pathologies,
        **annotations
    )

    return graph


def get_networks_with_permission(api):
    """Gets all networks tagged as public or uploaded by the current user
    
    :param DictionaryService api: 
    :return: A list of all networks tagged as public or uploaded by the current user
    :rtype: list[Network]
    """
    if not current_user.is_authenticated:
        return api.list_public_graphs()

    if current_user.admin or current_user.has_role('scai'):
        return api.list_graphs()

    networks = api.list_public_graphs()

    public_ids = {network.id for network in networks}

    for report in current_user.reports:
        if report.network_id in public_ids:
            continue
        networks.append(report.network)

    return networks


def build_dictionary_service_admin(app):
    """Dictionary Service Admin Functions"""
    manager = get_manager(app)
    api = get_api(app)

    @app.route('/admin/reload')
    @roles_required('admin')
    def run_reload():
        """Reloads the networks and supernetwork"""
        api.load_networks(force_reload=True)
        return jsonify({'status': 200})

    @app.route('/admin/enrich')
    @roles_required('admin')
    def run_enrich_authors():
        """Enriches information in network. Be patient"""
        fix_pubmed_citations(api.universe)
        return jsonify({'status': 200})

    @app.route('/admin/ensure/small')
    @roles_required('admin')
    def ensure_small_corpus():
        """Parses and stores the small corpus"""
        graph = from_url(SMALL_CORPUS_URL, manager=manager, citation_clearing=False, allow_nested=True)
        return try_insert_graph(manager, graph, api)

    @app.route('/admin/ensure/large')
    @roles_required('admin')
    def ensure_large_corpus():
        """Parses the large corpus"""
        graph = from_url(LARGE_CORPUS_URL, manager=manager, citation_clearing=False, allow_nested=True)
        return try_insert_graph(manager, graph, api)

    @app.route('/admin/ensure/abstract3')
    @roles_required('admin')
    def ensure_abstract3():
        """Parses and stores Selventa Example 3"""
        url = 'http://resources.openbel.org/belframework/20150611/knowledge/full_abstract3.bel'
        graph = from_url(url, manager=manager, citation_clearing=False, allow_nested=True)
        return try_insert_graph(manager, graph, api)

    @app.route('/admin/ensure/simple')
    @roles_required('admin')
    def ensure_simple():
        """Parses and stores the PyBEL Test BEL Script"""
        url = 'https://raw.githubusercontent.com/pybel/pybel/develop/tests/bel/test_bel.bel'
        graph = from_url(url, manager=manager)
        return try_insert_graph(manager, graph, api)

    @app.route('/admin/ensure/gfam')
    @roles_required('admin')
    def ensure_gfam():
        """Parses and stores the HGNC Gene Family Definitions"""
        graph = from_url(FRAUNHOFER_RESOURCES + 'gfam_members.bel', manager=manager)
        return try_insert_graph(manager, graph, api)

    @app.route('/admin/ensure/aetionomy')
    @roles_required('admin')
    def ensure_aetionomy():
        """Parses and stores the AETIONOMY resources from the Biological Model Store repository"""
        t = time.time()
        convert_recursive(os.path.join(os.environ[BMS_BASE], 'aetionomy'), connection=manager, upload=True,
                          enrich_citations=True)
        return jsonify({'status': 200, 'time': time.time() - t})

    @app.route('/admin/upload/aetionomy')
    @roles_required('admin')
    def upload_aetionomy():
        """Uploads the gpickles in the AETIONOMY section of the Biological Model Store repository"""
        t = time.time()
        upload_recursive(os.path.join(os.environ[BMS_BASE], 'aetionomy'), connection=manager)
        return jsonify({'status': 200, 'time': time.time() - t})

    @app.route('/admin/upload/selventa')
    @roles_required('admin')
    def upload_selventa():
        """Uploads the gpickles in the Selventa section of the Biological Model Store repository"""
        t = time.time()
        upload_recursive(os.path.join(os.environ[BMS_BASE], 'selventa'), connection=manager)
        return jsonify({'status': 200, 'time': time.time() - t})

    @app.route('/admin/list/bms/pickles')
    @roles_required('admin')
    def list_bms_pickles():
        """Lists the precompiled gpickles in the Biological Model Store repository"""
        return jsonify(list(get_paths_recursive(os.environ[BMS_BASE], extension='.gpickle')))

    @app.route('/admin/list/reporting')
    @roles_required('admin')
    def list_reporting():
        """Sends the reporting log as a text file"""
        return flask.send_file(os.path.join(PYBEL_LOG_DIR, 'reporting.txt'))

    @app.route('/admin/nuke/')
    @roles_required('admin')
    def nuke():
        """Destroys the database and recreates it"""
        log.info('nuking database')
        manager.drop_database()
        manager.create_all()
        log.info('restarting dictionary service')
        api.clear()
        log.info('... the dust settles')
        return jsonify({'status': 200})

    @app.route('/admin/network/make_public/<int:network_id>')
    @roles_accepted('admin', 'scai')
    def make_network_public(network_id):
        report = manager.session.query(Report).filter(Report.network_id == network_id).one()
        report.public = True
        manager.commit()

        flask.flash('Made {} public'.format(report.network))
        return redirect(url_for('view_networks'))

    @app.route('/api/network/make_public/<int:user_id>/<int:network_id>')
    @login_required
    def make_user_network_public(user_id, network_id):
        if current_user.id != user_id:
            return flask.abort(402)

        report = manager.session.query(Report).filter(Report.network_id == network_id, Report.user_id == user_id).one()
        report.public = True
        manager.commit()

        flask.flash('Made {} public'.format(report.network))
        return redirect(url_for('view_networks'))

    log.info('added dict service admin functions')


def build_api_admin(app):
    """API Admin functions"""
    manager = get_manager(app)

    @app.route('/admin/rollback')
    @roles_required('admin')
    def rollback():
        """Rolls back the transaction for when something bad happens"""
        manager.rollback()
        return jsonify({'status': 200})

    @app.route('/admin/manage/graphs/drop/<int:network_id>')
    @roles_required('admin')
    def drop_graph(network_id):
        """Drops a specific graph"""
        log.info('dropping graphs %s', network_id)
        manager.drop_graph(network_id)
        return jsonify({'status': 200})

    @app.route('/admin/manage/graphs/dropall')
    @roles_required('admin')
    def drop_graphs():
        """Drops all graphs"""
        log.info('dropping all graphs')
        manager.drop_graphs()
        return jsonify({'status': 200})

    @app.route('/admin/manage/namespaces/drop/<int:namespace_id>')
    @roles_required('admin')
    def drop_namespace(namespace_id):
        log.info('dropping namespace %s', namespace_id)
        manager.session.query(Namespace).filter(Namespace.id == namespace_id).delete()
        manager.session.commit()
        return jsonify({'status': 200})

    @app.route('/admin/manage/namespaces/dropall')
    @roles_required('admin')
    def drop_namespaces():
        """Drops all namespaces"""
        log.info('dropping all namespaces')
        manager.session.query(Namespace).delete()
        manager.session.commit()
        return jsonify({'status': 200})

    @app.route('/admin/manage/annotations/drop/<annotation_id>')
    @roles_required('admin')
    def drop_annotation(annotation_id):
        log.info('dropping annotation %s', annotation_id)
        manager.session.query(Annotation).filter(Annotation.id == annotation_id).delete()
        manager.session.commit()
        return jsonify({'status': 200})

    @app.route('/admin/manage/annotations/dropall')
    @roles_required('admin')
    def drop_annotations():
        """Drops all annotations"""
        log.info('dropping all annotations')
        manager.session.query(Annotation).delete()
        manager.session.commit()
        return jsonify({'status': 200})

    @app.route('/admin/config')
    @roles_required('admin')
    def view_config():
        return jsonify({k: str(v) for k, v in app.config.items()})

    log.info('added api admin functions')


def build_dictionary_service(app):
    """Builds the PyBEL Dictionary-Backed API Service.

    :param flask.Flask app: A Flask App
    :param bool check_version: Should the versions of the networks be checked during loading?
    """
    manager = get_manager(app)
    api = get_api(app)

    if app.config.get('PYBEL_DS_PRELOAD', True):
        log.info('preloading networks')
        api.load_networks(check_version=app.config.get('PYBEL_DS_CHECK_VERSION', True),
                          eager=app.config.get('PYBEL_DS_EAGER', False))
        log.info('pre-loaded the dict service')

    build_dictionary_service_admin(app)
    build_api_admin(app)

    # Web Pages

    @app.route('/', methods=['GET', 'POST'])
    def home():
        """Renders the home page"""
        return render_template('index.html')

    @app.route('/networks', methods=['GET', 'POST'])
    def view_networks():
        """Renders a page for the user to choose a network"""
        seed_subgraph_form = SeedSubgraphForm()
        seed_provenance_form = SeedProvenanceForm()

        if seed_subgraph_form.validate_on_submit() and seed_subgraph_form.submit_subgraph.data:
            seed_data_nodes = seed_subgraph_form.node_list.data.split(',')
            seed_method = seed_subgraph_form.seed_method.data
            filter_pathologies = seed_subgraph_form.filter_pathologies.data
            log.info('got subgraph seed: %s',
                     dict(nodes=seed_data_nodes, method=seed_method, filter_path=filter_pathologies))
            url = url_for('view_explorer', **{
                GRAPH_ID: '0',
                SEED_TYPE: seed_method,
                SEED_DATA_NODES: seed_data_nodes,
                FILTER_PATHOLOGIES: filter_pathologies,
                AUTOLOAD: 'yes',
            })
            log.info('redirecting to %s', url)
            return redirect(url)
        elif seed_provenance_form.validate_on_submit() and seed_provenance_form.submit_provenance.data:
            authors = sanitize_list_of_str(seed_provenance_form.author_list.data.split(','))
            pmids = sanitize_list_of_str(seed_provenance_form.pubmed_list.data.split(','))
            filter_pathologies = seed_provenance_form.filter_pathologies.data
            log.info('got prov: %s', dict(authors=authors, pmids=pmids))
            url = url_for('view_explorer', **{
                GRAPH_ID: '0',
                SEED_TYPE: SEED_TYPE_PROVENANCE,
                SEED_DATA_PMIDS: pmids,
                SEED_DATA_AUTHORS: authors,
                FILTER_PATHOLOGIES: filter_pathologies,
                AUTOLOAD: 'yes',
            })
            log.info('redirecting to %s', url)
            return redirect(url)

        networks = get_networks_with_permission(api)

        return flask.render_template(
            'network_list.html',
            networks=networks,
            provenance_form=seed_provenance_form,
            subgraph_form=seed_subgraph_form,
            analysis_enabled=True,
            current_user=current_user,
        )

    @app.route('/explore', methods=['GET'])
    def view_explorer():
        """Renders a page for the user to explore a network"""
        return flask.render_template('explorer.html')

    @app.route('/summary/<int:graph_id>')
    def view_summary(graph_id):
        """Renders a page with the parsing errors for a given BEL script"""
        try:
            network = manager.get_network_by_id(graph_id)
            graph = from_bytes(network.blob, check_version=app.config.get('PYBEL_DS_CHECK_VERSION'))
        except:
            flask.flash("Problem getting graph {}".format(graph_id), category='error')
            return redirect(url_for('view_summary'))

        return render_graph_summary(graph_id, graph, api)

    @app.route('/definitions')
    def view_definitions():
        """Displays a page listing the namespaces and annotations."""
        return render_template(
            'definitions_list.html',
            namespaces=manager.session.query(Namespace).order_by(Namespace.keyword).all(),
            annotations=manager.session.query(Annotation).order_by(Annotation.keyword).all(),
            current_user=current_user,
        )

    # Data Service

    @app.route('/api/network/list', methods=['GET'])
    def get_network_list():
        return jsonify(manager.list_graphs())

    @app.route('/api/summary/<int:network_id>')
    def get_number_nodes(network_id):
        """Gets a summary of the given network"""
        return jsonify(info_json(api.get_network(network_id)))

    @app.route('/api/network/', methods=['GET'])
    @login_required
    def get_network():
        """Builds a graph from the given network id and sends it in the given format"""
        graph = get_graph_from_request(api)
        return serve_network(graph, request.args.get(FORMAT))

    @app.route('/api/network/name/<int:network_id>')
    def get_network_id(network_id):
        """Returns network name given its id"""
        if network_id == 0:
            return ''

        graph = api.get_network(network_id)
        return jsonify(graph.name)

    @app.route('/api/network/<int:network_id>/drop')
    @login_required
    def drop_network(network_id):
        """Drops a given network"""
        if not current_user.admin:
            flask.abort(403)
        manager.drop_graph(network_id)
        flask.flash('Dropped network {}'.format(network_id))
        return redirect(url_for('view_networks'))

    @app.route('/api/tree/')
    @login_required
    def get_tree_api():
        """Builds the annotation tree data structure for a given graph"""
        graph_id = request.args.get(GRAPH_ID)
        return jsonify(get_tree_annotations(api.get_network(graph_id)))

    @app.route('/api/paths/')
    def get_paths_api():
        """Returns array of shortest/all paths given a source node and target node both belonging in the graph
        :return: JSON 
        """
        graph = get_graph_from_request(api)

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
            # TODO: Think about increasing the cutoff
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
        graph = get_graph_from_request(api)

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
        graph = get_graph_from_request(api)
        return jsonify(sorted(get_authors(graph)))

    @app.route('/api/pmids')
    def get_all_pmids():
        """Gets a list of all pubmed citation identifiers in the graph produced by the given URL parameters"""
        graph = get_graph_from_request(api)
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

    def _build_namespace_helper(graph, namespace, names):
        si = StringIO()

        write_namespace(
            namespace_name=namespace,
            namespace_keyword=namespace,
            namespace_domain='Other',
            author_name=graph.document.get(METADATA_AUTHORS),
            author_contact=graph.document.get(METADATA_CONTACT),
            citation_name=graph.document.get(METADATA_NAME),
            citation_description='This namespace was serialized by PyBEL Web',
            values=names,
            file=si
        )

        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = "attachment; filename={}.belns".format(namespace)
        output.headers["Content-type"] = "text/plain"
        return output

    @app.route('/api/namespace/builder/undefined/<int:graph_id>/<namespace>')
    def download_undefined_namespace(graph_id, namespace):
        """Outputs a namespace built for this undefined namespace"""
        graph = api.get_network(graph_id)
        names = get_undefined_namespace_names(graph, namespace)
        return _build_namespace_helper(graph, namespace, names)

    @app.route('/api/namespace/builder/incorrect/<int:graph_id>/<namespace>')
    def download_missing_namespace(graph_id, namespace):
        """Outputs a namespace built from the missing names in the given namespace"""
        graph = api.get_network(graph_id)
        names = get_incorrect_names(graph, namespace)
        return _build_namespace_helper(graph, namespace, names)

    @app.route('/overlap')
    def get_node_overlap_image():
        import pyupset as pyu
        import matplotlib.pyplot as plt
        import pandas as pd
        from six import BytesIO

        network_ids = request.args.get('networks')
        if not network_ids:
            return flask.abort(500)

        networks = [api.get_network(int(network_id.strip())) for network_id in network_ids.split(',')]

        data_dict = {network.name.replace('_', ' '): pd.DataFrame(network.nodes()) for network in networks}
        pyu.plot(data_dict)
        buf = BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        output = make_response(buf.getvalue())
        output.headers["Content-type"] = "image/png"
        return output

    log.info('Added dictionary service to %s', app)
