# -*- coding: utf-8 -*-

import logging
import time

import flask
from flask import request

from pybel import BELGraph, to_bytes
from pybel.parser import BelParser

__all__ = [
    'build_parser_app',
]

log = logging.getLogger(__name__)


def build_parser_app(app):
    """Builds parser app for sending and receiving BEL statements

    :type app: flask.Flask
    """
    bg = BELGraph()
    parser = BelParser(bg)

    @app.route('/parser/parse/<statement>', methods=['GET', 'POST'])
    def parse_bel(statement):
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
            return flask.jsonify(**res.asDict())
        except Exception as e:
            return "Exception: {}".format(e)

    @app.route('/parser/dump/bytes')
    def dump_bytes():
        return flask.Response(to_bytes(bg), mimetype='text/plain')

    @app.route('/parser/clear')
    def clear():
        """Clears the content of the current graph"""
        parser.clear()
        return "cleared"
