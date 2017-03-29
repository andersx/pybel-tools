# -*- coding: utf-8 -*-

"""
This module contains all of the services necessary through the PyBEL API Definition, backed by the PyBEL cache manager.
"""

# from .base_service import PybelService
from flask import Flask

from .db_service_utils import DatabaseService

# class DatabaseService(PybelService):#

#    def __init__(self):
#        pass

DATABASE_SERVICE = 'database_service'


def build_database_service_app(dsa):
    """Builds the PyBEL Dictionary-Backed API Service. Adds a latent PyBEL Dictionary service that can be retrieved
    with :func:`get_dict_service`

    :param dsa: A Flask App
    :type dsa: Flask
    """

    api = DatabaseService()
    dsa.config[DATABASE_SERVICE] = api

    @dsa.route('/networks', methods=['GET'])
    def list_networks():
        pass

    @dsa.route('/namespaces', methods=['GET'])
    def list_namespaces():
        pass

    @dsa.route('/namespaces/by_network/<int:network_id>', methods=['GET'])
    def namespaces_by_network(network_id):
        pass

    @dsa.route('/namespace/<definition_key>', methods=['GET'])
    def list_names(definition_key):
        pass

    @dsa.route('/annotations', methods=['GET'])
    def list_annotations():
        pass

    @dsa.route('/annotations/by_network/<int:network_id>', methods=['GET'])
    def annotations_by_network(network_id):
        pass

    @dsa.route('/annotation/<definition_key>', methods=['GET'])
    def list_annotation_names():
        pass

    @dsa.route('/citations', methods=['GET'])
    def list_citations():
        pass

    @dsa.route('/citations/by_network/<int:network_id>', methods=['GET'])
    def citations_by_network(network_id):
        pass

    @dsa.route('/edges/by_bel/statement/<statement_bel>', methods=['GET'])
    def edges_by_bel_statement(statement_bel):
        pass

    @dsa.route('/edges/by_bel/source/<source_bel>', methods=['GET'])
    def edges_by_bel_source(source_bel):
        pass

    @dsa.route('/edges/by_bel/target/<target_bel>', methods=['GET'])
    def edges_by_bel_target(target_bel):
        pass

    @dsa.route('/edges/by_network/<int:network_id>', methods=['GET'])
    def edges_by_network(network_id):
        pass

    @dsa.route('/edges/by_pmid/<int:pmid_id>', methods=['GET'])
    def edges_by_pmid(pmid_id):
        pass

    @dsa.route('/edges/by_author/<author>', methods=['GET'])
    def edges_by_author(author):
        pass

    @dsa.route('/edges/by_network_and_author/<int:network_id>/<author>', methods=['GET'])
    def edges_by_network_and_author(network_id, author):
        pass

    @dsa.route('/edges/by_network_and_pmid/<int:network_id>/<int:pmid_id>', methods=['GET'])
    def edges_by_network_and_pmid(network_id, pmid_id):
        pass

    @dsa.route('/edges/by_annotation/<annotation_name>/<annotation_value>', methods=['GET'])
    def edges_by_annotation(annotation_name, annotation_value):
        pass

    @dsa.route('/edges/by_network_and_annotation/<int:network_id>/<annotation_name>/<annotation_value>',
               methods=['GET'])
    def edges_by_network_and_annotation(network_id, annotation_name, annotation_value):
        pass

    @dsa.route('/nodes/by_bel/<node_bel>', methods=['GET'])
    def nodes_by_bel(node_bel):
        pass

    @dsa.route('/nodes/by_name/<node_name>', methods=['GET'])
    def nodes_by_name(node_name):
        pass

    @dsa.route('/nodes/by_namespace/<node_namespace>', methods=['GET'])
    def nodes_by_namespace(node_namespace):
        pass

    @dsa.route('/nodes/by_network/<int:network_id>', methods=['GET'])
    def nodes_by_network(network_id):
        pass

    @dsa.route('/path/by_bel/start_node/<node_bel>', methods=['GET'])
    def paths_by_start(node_bel):
        pass

    @dsa.route('/path/by_bel/end_node/<node_bel>', methods=['GET'])
    def paths_by_end(node_bel):
        pass

    @dsa.route('/path/by_bel/start_and_end/<start_bel>/<end_bel>', methods=['GET'])
    def paths(start_bel, end_bel):
        pass


app = Flask(__name__)
build_database_service_app(app)
