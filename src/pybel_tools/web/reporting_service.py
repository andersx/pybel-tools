# -*- coding: utf-8 -*-

import logging

from flask import render_template

from .extension import get_manager
from .models import Report

log = logging.getLogger(__name__)


def build_reporting_service(app):
    """Adds the endpoints for uploading pickle files

    :param flask.Flask app: A Flask application
    """
    manager = get_manager(app)

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
