# -*- coding: utf-8 -*-

import logging
import traceback

import flask
from flask import render_template, jsonify, Flask
from flask_bootstrap import Bootstrap
from sqlalchemy.exc import IntegrityError

log = logging.getLogger(__name__)


def render_upload_error(e):
    traceback_lines = traceback.format_exc().split('\n')
    return render_template(
        'parse_error.html',
        error_title='Upload Error',
        error_text=str(e),
        traceback_lines=traceback_lines
    )


def try_insert_graph(manager, graph):
    """Inserts a graph and sends an okay message if success. else renders upload page
    
    :param manager: 
    :type manager: pybel.manager.cache.CacheManager
    :param graph: 
    :type graph: pybel.BELGraph
    :return: HTTP response for flask rote
    """
    try:
        network = manager.insert_graph(graph)
        return jsonify({
            'status': 200,
            'network_id': network.id
        })
    except IntegrityError as e:
        flask.flash("Graph with same Name/Version already exists. Try bumping the version number.")
        log.exception('Integrity error')
        manager.rollback()
        return render_upload_error(e)
    except Exception as e:
        flask.flash("Error storing in database")
        log.exception('Upload error')
        return render_upload_error(e)


def get_app():
    """Builds a Flask app for the PyBEL web service
    
    :rtype: flask.Flask
    """
    app = Flask(__name__)
    log.debug('made app %s', app)
    Bootstrap(app)
    log.debug('added bootstrap to app %s', app)
    return app


def sanitize_list_of_str(l):
    """Strips all strings in a list and filters to the non-empty ones
    
    :type l: list[str]
    :rtype: list[str]
    """
    return [e for e in (e.strip() for e in l) if e]
