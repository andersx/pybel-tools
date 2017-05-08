# -*- coding: utf-8 -*-

import logging

from flask import render_template

from .models import Report

log = logging.getLogger(__name__)


def build_reporting_service(app, manager):
    """Adds the endpoints for uploading pickle files

    :param flask.Flask app: A Flask application
    :param manager: A PyBEL cache manager
    :type manager: pybel.manager.cache.CacheManager
    """

    @app.route('/reporting', methods=['GET'])
    def view_reports(network_name=None):
        """Shows the uploading reporting"""
        reports = manager.session.query(Report).order_by(Report.created).all()
        return render_template('reporting.html', reports=reports)

    @app.route('/reporting/user/<username>', methods=['GET'])
    def view_individual_report(username):
        reports = manager.session.query(Report).filter_by(Report.username == username).order_by(Report.created).all()
        return render_template('reporting.html', reports=reports)

    log.info('Added reporting service to %s', app)
