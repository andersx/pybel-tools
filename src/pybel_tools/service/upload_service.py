# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import logging

import flask
from flask import Flask, render_template
from flask import jsonify
from sqlalchemy.exc import IntegrityError

import pybel
from .forms import UploadForm
from .utils import render_upload_error, try_insert_graph

log = logging.getLogger(__name__)


def build_pickle_uploader_service(app, manager):
    """Adds the endpoints for uploading pickle files

    :param app: A Flask application
    :type app: Flask
    :param manager: A PyBEL cache manager
    :type manager: pybel.manager.cache.CacheManager
    """

    @app.route('/upload', methods=('GET', 'POST'))
    def view_upload():
        """An upload form for a BEL script"""
        form = UploadForm()

        if not form.validate_on_submit():
            return render_template('upload.html', form=form)

        log.info('Running on %s', form.file.data.filename)

        try:
            graph_bytes = form.file.data.read()
            s = graph_bytes
            graph = pybel.from_bytes(s)
        except Exception as e:
            log.exception('Gpickle error')
            return render_upload_error(e)

        return try_insert_graph(manager, graph)

    log.info('Added pickle uploader endpoint to %s', app)
