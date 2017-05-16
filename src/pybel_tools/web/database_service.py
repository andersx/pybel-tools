# -*- coding: utf-8 -*-

"""This module runs the database-backed PyBEL API"""

import logging

import flask
from flask import Flask
from flask import jsonify
from flask import request

from .database_service_utils import DatabaseService

log = logging.getLogger(__name__)

DATABASE_SERVICE = 'database_service'


def get_database_service(dsa):
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


def build_database_service(app, manager):
    """Builds the PyBEL Database-Backed API Service.

    :param app: A Flask App
    :type app: Flask
    :param manager: A PyBEL cache manager
    :type manager: pybel.manager.cache.CacheManager
    """
    db_api = DatabaseService(manager=manager)

    @app.route('/api/database/networks', methods=['GET'])
    def get_networks_args():
        result = db_api.get_networks()

        return jsonify(result)

    @app.route('/api/database/namespaces', methods=['GET'])
    def get_namespaces_args():
        if 'network_id' in request.args:
            network_id = int(request.args.get('network_id'))
            result = db_api.get_namespaces(network_id=network_id)
        elif 'keyword' in request.args:
            keyword = request.args.get('keyword')
            result = db_api.get_namespaces(name_list=True, keyword=keyword)
        else:
            result = db_api.get_namespaces()

        return jsonify(result)

    @app.route('/api/database/annotations', methods=['GET'])
    def get_annotations_args():
        if 'network_id' in request.args:
            network_id = int(request.args.get('network_id'))
            result = db_api.get_annotations(network_id=network_id)
        elif 'keyword' in request.args:
            keyword = request.args.get('keyword')
            result = db_api.get_annotations(name_list=True, keyword=keyword)
        else:
            result = db_api.get_annotations()

        return jsonify(result)

    @app.route('/api/database/citations', methods=['GET'])
    def get_citations_args():
        if request.args.get('network_id'):
            network_id = int(request.args.get('network_id'))
            result = db_api.get_citations(network_id=network_id)
        else:
            result = db_api.get_citations(author=request.args.get('author'))

        return jsonify(result)

    @app.route('/api/database/edges', methods=['GET'])
    def get_edges_args():
        result = None
        offset = request.args.get('offset')
        start_str, stop_str = offset.split(':') if offset else [0, 500]
        start = int(start_str) if start_str else 0
        stop = int(stop_str) if stop_str else None
        if 'statement' in request.args:
            statement_bel = request.args.get('statement')
            result = db_api.get_edges(statement=statement_bel)
        elif 'network_id' in request.args:
            network_id = int(request.args.get('network_id'))
            result = db_api.get_edges(network_id, offset_start=start, offset_end=stop)
        elif 'annotation' in request.args:
            annotation = request.args.get('annotation')
            if annotation:
                annotation_keyword, annotation_name = annotation.split(':')
                result = db_api.get_edges(annotations={annotation_keyword: annotation_name})
        if result is None:
            source_bel = request.args.get('source')
            target_bel = request.args.get('target')
            relation = request.args.get('relation')
            pmid = request.args.get('pmid')
            author = request.args.get('author')
            result = db_api.get_edges(pmid=pmid, source=source_bel, target=target_bel, relation=relation, author=author)

        return jsonify(result)

    @app.route('/api/database/nodes', methods=['GET'])
    def get_nodes_args():
        node_bel = request.args.get('bel')
        namespace = request.args.get('namespace')
        name = request.args.get('name')

        if 'network_id' in request.args:
            offset = request.args.get('offset')
            start_str, stop_str = offset.split(':') if offset else [0, 500]
            start = int(start_str) if start_str else 0
            stop = int(stop_str) if stop_str else None
            network_id = int(request.args.get('network_id'))
            result = db_api.get_nodes(network_id=network_id, offset_start=start, offset_end=stop)
        else:
            result = db_api.get_nodes(bel=node_bel, namespace=namespace, name=name)

        return jsonify(result)

    log.info('Added database service to %s', app)

    # return api
