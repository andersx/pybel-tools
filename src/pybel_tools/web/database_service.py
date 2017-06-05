# -*- coding: utf-8 -*-

"""This module runs the database-backed PyBEL API"""

from flask import Blueprint
from flask import jsonify
from werkzeug.local import LocalProxy

from .utils import get_current_manager, get_api

api_blueprint = Blueprint('database_service', __name__)
manager = LocalProxy(get_current_manager)
api = LocalProxy(get_api)


@api_blueprint.route('/api/namespaces', methods=['GET'])
def list_namespaces():
    all_namespaces = api.query_namespaces()
    return jsonify(all_namespaces)


@api_blueprint.route('/api/namespaces/by_network/<int:network_id>', methods=['GET'])
def namespaces_by_network(network_id):
    network_namespaces = api.query_namespaces(network_id=network_id)
    return jsonify(network_namespaces)


@api_blueprint.route('/api/namespace/<keyword>', methods=['GET'])
def list_names(keyword):
    names = api.query_namespaces(name_list=True, keyword=keyword)
    return jsonify(names)


@api_blueprint.route('/api/annotations', methods=['GET'])
def list_annotations():
    all_annotations = api.query_annotations()
    return jsonify(all_annotations)


@api_blueprint.route('/api/annotations/by_network/<int:network_id>', methods=['GET'])
def annotations_by_network(network_id):
    network_annotations = api.query_annotations(network_id=network_id)
    return jsonify(network_annotations)


@api_blueprint.route('/api/annotation/<keyword>', methods=['GET'])
def list_annotation_names(keyword):
    annotation_names = api.query_annotations(name_list=True, keyword=keyword)
    return jsonify(annotation_names)


@api_blueprint.route('/api/citations', methods=['GET'])
def list_citations():
    citations = api.query_citations()
    return jsonify(citations)


@api_blueprint.route('/api/citations/by_network/<int:network_id>', methods=['GET'])
def citations_by_network(network_id):
    citations = api.query_citations(network_id=network_id)
    return jsonify(citations)


@api_blueprint.route('/api/citations/by_author/<author>', methods=['GET'])
def list_citations_by_author(author):
    citations = api.query_citations(author=author)
    return jsonify(citations)


@api_blueprint.route('/api/edges/by_bel/statement/<statement_bel>', methods=['GET'])
def edges_by_bel_statement(statement_bel):
    edges = api.query_edges(statement=statement_bel)
    return jsonify(edges)


@api_blueprint.route('/api/edges/by_bel/source/<source_bel>', methods=['GET'])
def edges_by_bel_source(source_bel):
    edges = api.query_edges(source=source_bel)
    return jsonify(edges)


@api_blueprint.route('/api/edges/by_bel/target/<target_bel>', methods=['GET'])
def edges_by_bel_target(target_bel):
    edges = api.query_edges(target=target_bel)
    return jsonify(edges)


@api_blueprint.route('/api/edges/by_network/<int:network_id>', methods=['GET'])
def edges_by_network(network_id):
    edges = api.query_edges(network_id=network_id)
    return jsonify(edges)


@api_blueprint.route('/api/edges/by_network/<int:network_id>/offset/<int:offset_start>/<int:offset_end>',
                     methods=['GET'])
def edges_by_network_offset(network_id, offset_start, offset_end):
    edges = api.query_edges(network_id=network_id, offset_start=offset_start, offset_end=offset_end)
    return jsonify(edges)


@api_blueprint.route('/api/edges/by_pmid/<int:pmid>', methods=['GET'])
def edges_by_pmid(pmid):
    edges = api.query_edges(pmid=pmid)
    return jsonify(edges)


@api_blueprint.route('/api/edges/by_author/<author>', methods=['GET'])
def edges_by_author(author):
    edges = api.query_edges(author=author)
    return jsonify(edges)


@api_blueprint.route('/api/edges/by_annotation/<annotation_name>/<annotation_value>', methods=['GET'])
def edges_by_annotation(annotation_name, annotation_value):
    edges = api.query_edges(annotations={annotation_name: annotation_value})
    return jsonify(edges)


@api_blueprint.route('/api/nodes/by_bel/<node_bel>', methods=['GET'])
def nodes_by_bel(node_bel):
    nodes = api.query_nodes(bel=node_bel)
    return jsonify(nodes)


@api_blueprint.route('/api/nodes/by_name/<node_name>', methods=['GET'])
def nodes_by_name(node_name):
    nodes = api.query_nodes(name=node_name)
    return jsonify(nodes)


@api_blueprint.route('/api/nodes/by_namespace/<node_namespace>', methods=['GET'])
def nodes_by_namespace(node_namespace):
    nodes = api.query_nodes(namespace=node_namespace)
    return jsonify(nodes)


@api_blueprint.route('/api/nodes/by_defined_name/<node_namespace>/<node_name>', methods=['GET'])
def nodes_by_namespace_name(node_namespace, node_name):
    nodes = api.query_nodes(namespace=node_namespace, name=node_name)
    return jsonify(nodes)


@api_blueprint.route('/api/nodes/by_network/<int:network_id>', methods=['GET'])
def nodes_by_network(network_id):
    nodes = api.query_nodes(network_id=network_id)
    return jsonify(nodes)
