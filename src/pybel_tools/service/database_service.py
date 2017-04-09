# -*- coding: utf-8 -*-

"""This module runs the database-backed PyBEL API"""

import flask
from flask import Flask
from flask import jsonify
from flask_bootstrap import Bootstrap

from .database_service_utils import DatabaseService
from ..web.utils import get_cache_manager

DATABASE_SERVICE = 'database_service'


def get_db_service(dsa):
    """Gets the latent PyBEL Dictionary Service from a Flask app

    :param dsa: A Flask app
    :type dsa: Flask
    :return: The latent dictionary service
    :rtype: DictionaryService
    """
    return dsa.config[DATABASE_SERVICE]


def set_database_service(app, service):
    """Adds the dictionary service to the config of the given Flask app

    :param app: A Flask app
    :type app: flask.Flask
    :param service: The Dictionary Service
    :type service: DictionaryService
    """
    app.config[DATABASE_SERVICE] = service


def build_database_service_app(app):
    """Builds the PyBEL Database-Backed API Service.

    :param app: A Flask App
    :type app: Flask
    """
    manager = get_cache_manager(app)
    api = DatabaseService(manager)
    set_database_service(app, api)

    @app.route('/api/namespaces', methods=['GET'])
    def list_namespaces():
        all_namespaces = api.get_namespaces()
        return jsonify(all_namespaces)

    @app.route('/api/namespaces/by_network/<int:network_id>', methods=['GET'])
    def namespaces_by_network(network_id):
        network_namespaces = api.get_namespaces(network_id=network_id)
        return jsonify(network_namespaces)

    @app.route('/api/namespace/<keyword>', methods=['GET'])
    def list_names(keyword):
        names = api.get_namespaces(name_list=True, keyword=keyword)
        return jsonify(names)

    @app.route('/api/annotations', methods=['GET'])
    def list_annotations():
        all_annotations = api.get_annotations()
        return jsonify(all_annotations)

    @app.route('/api/annotations/by_network/<int:network_id>', methods=['GET'])
    def annotations_by_network(network_id):
        network_annotations = api.get_annotations(network_id=network_id)
        return jsonify(network_annotations)

    @app.route('/api/annotation/<keyword>', methods=['GET'])
    def list_annotation_names(keyword):
        annotation_names = api.get_annotations(name_list=True, keyword=keyword)
        return jsonify(annotation_names)

    @app.route('/api/citations', methods=['GET'])
    def list_citations():
        citations = api.get_citations()
        return jsonify(citations)

    @app.route('/api/citations/by_network/<int:network_id>', methods=['GET'])
    def citations_by_network(network_id):
        citations = api.get_citations(network_id=network_id)
        return jsonify(citations)

    @app.route('/api/citations/by_author/<author>', methods=['GET'])
    def list_citations_by_author(author):
        citations = api.get_citations(author=author)
        return jsonify(citations)

    @app.route('/api/edges/by_bel/statement/<statement_bel>', methods=['GET'])
    def edges_by_bel_statement(statement_bel):
        edges = api.get_edges(statement=statement_bel)
        return jsonify(edges)

    @app.route('/api/edges/by_bel/source/<source_bel>', methods=['GET'])
    def edges_by_bel_source(source_bel):
        edges = api.get_edges(source=source_bel)
        return jsonify(edges)

    @app.route('/api/edges/by_bel/target/<target_bel>', methods=['GET'])
    def edges_by_bel_target(target_bel):
        edges = api.get_edges(target=target_bel)
        return jsonify(edges)

    @app.route('/api/edges/by_network/<int:network_id>', methods=['GET'])
    def edges_by_network(network_id):
        edges = api.get_edges(network_id=network_id)
        return jsonify(edges)

    @app.route('/api/edges/by_network/<int:network_id>/offset/<int:offset_start>/<int:offset_end>', methods=['GET'])
    def edges_by_network_offset(network_id, offset_start, offset_end):
        edges = api.get_edges(network_id=network_id, offset_start=offset_start, offset_end=offset_end)
        return jsonify(edges)

    @app.route('/api/edges/by_pmid/<int:pmid>', methods=['GET'])
    def edges_by_pmid(pmid):
        edges = api.get_edges(pmid=pmid)
        return jsonify(edges)

    @app.route('/api/edges/by_author/<author>', methods=['GET'])
    def edges_by_author(author):
        edges = api.get_edges(author=author)
        return jsonify(edges)

    @app.route('/api/edges/by_annotation/<annotation_name>/<annotation_value>', methods=['GET'])
    def edges_by_annotation(annotation_name, annotation_value):
        edges = api.get_edges(annotations={annotation_name: annotation_value})
        return jsonify(edges)

    @app.route('/api/nodes/by_bel/<node_bel>', methods=['GET'])
    def nodes_by_bel(node_bel):
        nodes = api.get_nodes(bel=node_bel)
        return jsonify(nodes)

    @app.route('/api/nodes/by_name/<node_name>', methods=['GET'])
    def nodes_by_name(node_name):
        nodes = api.get_nodes(name=node_name)
        return jsonify(nodes)

    @app.route('/api/nodes/by_namespace/<node_namespace>', methods=['GET'])
    def nodes_by_namespace(node_namespace):
        nodes = api.get_nodes(namespace=node_namespace)
        return jsonify(nodes)

    @app.route('/api/nodes/by_defined_name/<node_namespace>/<node_name>', methods=['GET'])
    def nodes_by_namespace_name(node_namespace, node_name):
        nodes = api.get_nodes(namespace=node_namespace, name=node_name)
        return jsonify(nodes)

    @app.route('/api/nodes/by_network/<int:network_id>', methods=['GET'])
    def nodes_by_network(network_id):
        nodes = api.get_nodes(network_id=network_id)
        return jsonify(nodes)


def get_app():
    app = Flask(__name__)
    Bootstrap(app)
    return app
