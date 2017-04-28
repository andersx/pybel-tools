# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import codecs
import logging
import time
import traceback

import flask
import requests
from flask import Flask, render_template
from sqlalchemy.exc import IntegrityError

from pybel import from_lines
from pybel.parser.parse_exceptions import InconsistientDefinitionError
from .forms import CompileForm
from .utils import render_graph_summary
from ..mutation.metadata import add_canonical_names

log = logging.getLogger(__name__)


def render_error(exception):
    traceback_lines = traceback.format_exc().split('\n')
    return render_template('parse_error.html', error_text=str(exception), traceback_lines=traceback_lines)


def build_synchronous_compiler_service(app, manager, enable_cache=True):
    """Adds the endpoints for a synchronous web validation web app

    :param app: A Flask application
    :type app: Flask
    :param manager: A PyBEL cache manager
    :type manager: pybel.manager.cache.CacheManager
    :param enable_cache: Should the user be given the option to cache graphs?
    :type enable_cache: bool
    """

    @app.route('/compile', methods=('GET', 'POST'))
    def view_compile():
        """An upload form for a BEL script"""
        form = CompileForm(save_network=True)

        if not form.validate_on_submit():
            return render_template('compile.html', form=form)

        log.info('Running on %s', form.file.data.filename)

        t = time.time()

        # Decode the file with the given decoding (utf-8 is default)
        lines = codecs.iterdecode(form.file.data.stream, form.encoding.data)

        try:
            graph = from_lines(
                lines,
                manager=manager,
                allow_nested=form.allow_nested.data,
                citation_clearing=(not form.citation_clearing.data)
            )
            add_canonical_names(graph)
        except requests.exceptions.ConnectionError as e:
            flask.flash("Resource doesn't exist", category='error')
            return render_error(e)
        except InconsistientDefinitionError as e:
            flask.flash('Duplicate definition: {}'.format(e.definition), category='error')
            return render_error(e)
        except Exception as e:
            return render_error(e)

        if not enable_cache:
            flask.flash('Sorry, storing data is not enabled currently', category='error')
            return render_graph_summary(0, graph)

        if not form.save_network.data and not form.save_edge_store.data:
            return render_graph_summary(0, graph)

        try:
            network = manager.insert_graph(graph, store_parts=form.save_edge_store.data)
            network_id = network.id
            log.info('Done storing %s [%d]', form.file.data.filename, network_id)
        except IntegrityError as e:
            flask.flash("A praph with same name and version already exists. Try bumping the version number.",
                        category='error')
            log.warning("Integrity error - can't store duplicate: %s v%s", graph.name, graph.version)
            manager.rollback()
            return render_error(e)
        except Exception as e:
            flask.flash("Error storing in database", category='error')
            return render_error(e)

        return render_graph_summary(network_id, graph)

    log.info('Added synchronous validator to %s', app)
