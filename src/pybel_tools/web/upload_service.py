# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import logging

from flask import render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

import pybel
from .constants import integrity_message
from .forms import UploadForm
from .models import add_network_reporting

log = logging.getLogger(__name__)


def build_pickle_uploader_service(app, manager):
    """Adds the endpoints for uploading pickle files

    :param flask.Flask app: A Flask application
    :param manager: A PyBEL cache manager
    :type manager: pybel.manager.cache.CacheManager
    """

    @app.route('/upload', methods=['GET', 'POST'])
    @login_required
    def view_upload():
        """An upload form for a BEL script"""
        form = UploadForm()

        if not form.validate_on_submit():
            return render_template('upload.html', form=form, current_user=current_user)

        log.info('uploading %s', form.file.data.filename)

        try:
            graph_bytes = form.file.data.read()
            graph = pybel.from_bytes(graph_bytes)
        except Exception as e:
            log.exception('gpickle error')
            flash('The given file was not able to be unpickled [{}]'.format(str(e)), category='error')
            return redirect(url_for('view_upload'))

        try:
            network = manager.insert_graph(graph)
        except IntegrityError:
            log.exception('integrity error')
            flash(integrity_message.format(graph.name, graph.version), category='error')
            manager.rollback()
            return redirect(url_for('view_upload'))
        except Exception as e:
            log.exception('upload error')
            flash("Error storing in database [{}]".format(e), category='error')
            return redirect(url_for('view_upload'))

        log.info('done uploading %s [%d]', form.file.data.filename, network.id)

        try:
            add_network_reporting(manager, network, current_user.name, current_user.username, graph.number_of_nodes(),
                                  graph.number_of_edges(), len(graph.warnings), precompiled=True)
        except IntegrityError:
            log.exception('integrity error')
            flash('problem with reporting service', category='warning')
            manager.rollback()

        return redirect(url_for('view_summary', graph_id=network.id))

    log.info('Added pickle uploader endpoint to %s', app)
