# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import logging
import traceback

import flask
from flask import Flask, render_template
from flask import jsonify
from sqlalchemy.exc import IntegrityError

import pybel
from .forms import UploadForm
from ..web.utils import get_cache_manager

log = logging.getLogger(__name__)


def render_upload_error(e):
    traceback_lines = traceback.format_exc().split('\n')
    return render_template(
        'parse_error.html',
        error_title='Upload Error',
        error_text=str(e),
        traceback_lines=traceback_lines
    )


def build_pickle_uploader_service(app, manager=None):
    """Adds the endpoints for uploading pickle files

    :param app: A Flask application
    :type app: Flask
    :param manager: A PyBEL cache manager
    :type manager: pybel.manager.cache.CacheManager
    """
    manager = get_cache_manager(app) if manager is None else manager

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

        try:
            manager.insert_graph(graph)
        except IntegrityError as e:
            flask.flash("Graph with same Name/Version already exists. Try bumping the version number.")
            log.exception('Integrity error')
            manager.rollback()
            return render_upload_error(e)
        except Exception as e:
            flask.flash("Error storing in database")
            log.exception('Upload error')
            return render_upload_error(e)

        return jsonify({'status', 'okay'})

    log.info('Added pickle uploader endpoint to %s', app)
