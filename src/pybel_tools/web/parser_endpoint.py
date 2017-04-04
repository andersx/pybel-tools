# -*- coding: utf-8 -*-

import logging
import time

import flask
from flask import request, jsonify

from pybel import BELGraph, to_bytes
from pybel.parser import BelParser

__all__ = [
    'build_parser_app',
]

log = logging.getLogger(__name__)


def build_parser_app(app):
    """Builds parser app for sending and receiving BEL statements
    
    :param app: A Flask app
    :type app: flask.Flask
    """
    bg = BELGraph()
    parser = BelParser(bg)

    @app.route('/api/parser/parse/<statement>', methods=['GET', 'POST'])
    def parse_bel(statement):
        """Parses a URL-encoded BEL statement"""
        parser.control_parser.clear()
        parser.control_parser.annotations.update({
            'added': str(time.asctime()),
            'ip': request.remote_addr,
            'host': request.host,
            'user': request.remote_user
        })
        parser.control_parser.annotations.update(request.args)
        try:
            res = parser.statement.parseString(statement)
            return jsonify(**res.asDict())
        except Exception as e:
            return "Exception: {}".format(e)

    @app.route('/api/parser/dump/bytes')
    def dump_bytes():
        """Dumps the internal graph as a gpickle"""
        return flask.Response(to_bytes(bg), mimetype='text/plain')

    @app.route('/api/parser/clear')
    def clear():
        """Clears the content of the internal graph"""
        parser.clear()
        return jsonify({'status': 'ok'})
