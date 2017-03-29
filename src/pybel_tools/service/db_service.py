# -*- coding: utf-8 -*-

"""This module runs the database-backed PyBEL API"""

import flask
from flask import Flask

from .db_service_utils import DatabaseService

DATABASE_SERVICE = 'database_service'


def build_database_service_app(dsa):
    """Builds the PyBEL Database-Backed API Service.

    :param dsa: A Flask App
    :type dsa: Flask
    """

    api = DatabaseService()
    dsa.config[DATABASE_SERVICE] = api

    @dsa.route('/networks', methods=['GET'])
    def list_networks():
        nids = api.get_network_ids()
        return flask.render_template('network_list.html', nids=nids)

    @dsa.route('/namespaces', methods=['GET'])
    def list_namespaces():
        all_namespaces = api.get_namespaces()
        return all_namespaces

    @dsa.route('/namespaces/by_network/<int:network_id>', methods=['GET'])
    def namespaces_by_network(network_id):
        network_namespaces = api.get_namespaces(network_id=network_id)
        return network_namespaces

    @dsa.route('/namespace/<definition_key>', methods=['GET'])
    def list_names(definition_key):
        names = api.get_namespaces(name_list=True, namespace_key=definition_key)
        return names

    @dsa.route('/annotations', methods=['GET'])
    def list_annotations():
        all_annotations = api.get_annotations()
        return all_annotations

    @dsa.route('/annotations/by_network/<int:network_id>', methods=['GET'])
    def annotations_by_network(network_id):
        network_annotations = api.get_annotations(network_id=network_id)
        return network_annotations

    @dsa.route('/annotation/<definition_key>', methods=['GET'])
    def list_annotation_names(definition_key):
        annotation_names = api.get_annotations(annotation_names=True, annotation_key=definition_key)
        return annotation_names

    @dsa.route('/citations', methods=['GET'])
    def list_citations():
        citations = api.get_citations()
        return citations

    @dsa.route('/citations/by_network/<int:network_id>', methods=['GET'])
    def citations_by_network(network_id):
        citations = api.get_citations(network_id=network_id)
        return citations

    @dsa.route('/citations/by_author/<author>', methods=['GET'])
    def list_citations(author):
        citations = api.get_citations(author=author)
        return citations

    @dsa.route('/edges/by_bel/statement/<statement_bel>', methods=['GET'])
    def edges_by_bel_statement(statement_bel):
        edges = api.get_edges(statement=statement_bel)
        return edges

    @dsa.route('/edges/by_bel/source/<source_bel>', methods=['GET'])
    def edges_by_bel_source(source_bel):
        edges = api.get_edges(source=source_bel)
        return edges

    @dsa.route('/edges/by_bel/target/<target_bel>', methods=['GET'])
    def edges_by_bel_target(target_bel):
        edges = api.get_edges(target=target_bel)
        return edges

    @dsa.route('/edges/by_network/<int:network_id>', methods=['GET'])
    def edges_by_network(network_id):
        edges = api.get_edges(network_id=network_id)
        return edges

    @dsa.route('/edges/by_pmid/<int:pmid_id>', methods=['GET'])
    def edges_by_pmid(pmid_id):
        edges = api.get_edges(pmid_id=pmid_id)
        return edges

    @dsa.route('/edges/by_author/<author>', methods=['GET'])
    def edges_by_author(author):
        edges = api.get_edges(author=author)
        return edges

    @dsa.route('/edges/by_network_and_author/<int:network_id>/<author>', methods=['GET'])
    def edges_by_network_and_author(network_id, author):
        edges = api.get_edges(network_id=network_id, author=author)
        return edges

    @dsa.route('/edges/by_network_and_pmid/<int:network_id>/<int:pmid_id>', methods=['GET'])
    def edges_by_network_and_pmid(network_id, pmid_id):
        edges = api.get_edges(network_id=network_id, pmid_id=pmid_id)
        return edges

    @dsa.route('/edges/by_annotation/<annotation_name>/<annotation_value>', methods=['GET'])
    def edges_by_annotation(annotation_name, annotation_value):
        edges = api.get_edges(annotations={annotation_name: annotation_value})
        return edges

    @dsa.route('/edges/by_network_and_annotation/<int:network_id>/<annotation_name>/<annotation_value>',
               methods=['GET'])
    def edges_by_network_and_annotation(network_id, annotation_name, annotation_value):
        edges = api.get_edges(network_id=network_id, annotations={annotation_name: annotation_value})
        return edges

    @dsa.route('/nodes/by_bel/<node_bel>', methods=['GET'])
    def nodes_by_bel(node_bel):
        nodes = api.get_nodes(bel=node_bel)
        return nodes

    @dsa.route('/nodes/by_name/<node_name>', methods=['GET'])
    def nodes_by_name(node_name):
        nodes = api.get_nodes(name=node_name)
        return nodes

    @dsa.route('/nodes/by_namespace/<node_namespace>', methods=['GET'])
    def nodes_by_namespace(node_namespace):
        nodes = api.get_nodes(namespace=node_namespace)
        return nodes

    @dsa.route('/nodes/by_defined_name/<node_namespace>/<node_name>', methods=['GET'])
    def nodes_by_namespace(node_namespace, node_name):
        nodes = api.get_nodes(namespace=node_namespace, name=node_name)
        return nodes

    @dsa.route('/nodes/by_network/<int:network_id>', methods=['GET'])
    def nodes_by_network(network_id):
        nodes = api.get_nodes(network_id=network_id)
        return nodes

    @dsa.route('/path/by_bel/start_node/<node_bel>', methods=['GET'])
    def paths_by_start(node_bel):
        paths = api.get_paths(start_node=node_bel)
        return paths

    @dsa.route('/path/by_bel/end_node/<node_bel>', methods=['GET'])
    def paths_by_end(node_bel):
        paths = api.get_paths(end_node=node_bel)
        return paths

    @dsa.route('/path/by_bel/start_and_end/<start_bel>/<end_bel>', methods=['GET'])
    def paths(start_bel, end_bel):
        paths = api.get_paths(start_node=start_bel, end_node=end_bel)
        return paths


app = Flask(__name__)
build_database_service_app(app)
