# -*- coding: utf-8 -*-

import logging

from flask import render_template

from .models import NetworkUser

log = logging.getLogger(__name__)


def build_reporting_service(app, manager):
    """Adds the endpoints for uploading pickle files

    :param flask.Flask app: A Flask application
    :param manager: A PyBEL cache manager
    :type manager: pybel.manager.cache.CacheManager
    """

    @app.route('/reporting', methods=['GET'])
    @app.route('/reporting/<network_name>', methods=['GET'])
    def view_reports(network_name=None):
        """Shows the uploading reporting"""
        if network_name is None:
            reports = manager.session.query(NetworkUser).order_by(NetworkUser.created).all()
        else:
            reports = manager.session.query(NetworkUser).filter_by(NetworkUser.network.name == network_name).order_by(
                NetworkUser.created).all()

        return render_template('reporting.html', reports=reports)

    log.info('Added reporting service to %s', app)
