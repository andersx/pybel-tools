# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import codecs
import logging
import traceback

import flask
import requests
from flask import Flask, render_template
from sqlalchemy.exc import IntegrityError

from pybel import from_lines
from pybel_tools.service.forms import CompileForm
from ..summary import count_functions, count_relations, count_error_types
from ..utils import prepare_c3
from ..web.utils import get_cache_manager

log = logging.getLogger(__name__)

import time


def render_error(exception):
    traceback_lines = traceback.format_exc().split('\n')
    return render_template('parse_error.html', error_text=str(exception), traceback_lines=traceback_lines)


def build_synchronous_compiler_service(app, enable_cache=True):
    """Adds the endpoints for a synchronous web validation web app

    :param app: A Flask application
    :type app: Flask
    :param enable_cache: Should the user be given the option to cache graphs?
    :type enable_cache: bool
    """
    manager = get_cache_manager(app)

    @app.route('/compile', methods=('GET', 'POST'))
    def view_compile():
        """An upload form for a BEL script"""
        form = CompileForm()

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
        except requests.exceptions.ConnectionError as e:
            flask.flash("Resource doesn't exist")
            return render_error(e)
        except Exception as e:
            return render_error(e)

        if not enable_cache and (form.save_network.data or form.save_edge_store.data):
            flask.flash('Sorry, storing data is not enabled currently')
            return render_template(
                'summary.html',
                chart_1_data=prepare_c3(count_functions(graph), 'Entity Type'),
                chart_2_data=prepare_c3(count_relations(graph), 'Relationship Type'),
                chart_3_data=prepare_c3(count_error_types(graph), 'Error Type'),
                graph=graph,
                filename='{} (v{})'.format(graph.name, graph.version),
                time='{:.2f}'.format(time.time() - t)
            )

        try:
            network = manager.insert_graph(graph, store_parts=form.save_edge_store.data)
            network_id = network.id
            log.info('Done storing %s [%d]', form.file.data.filename, network_id)
        except IntegrityError as e:
            flask.flash("Graph with same Name/Version already exists. Try bumping the version number.")
            manager.rollback()
            return render_error(e)
        except Exception as e:
            flask.flash("Error storing in database")
            return render_error(e)

        return render_template(
            'summary.html',
            chart_1_data=prepare_c3(count_functions(graph), 'Entity Type'),
            chart_2_data=prepare_c3(count_relations(graph), 'Relationship Type'),
            chart_3_data=prepare_c3(count_error_types(graph), 'Error Type'),
            graph=graph,
            filename='{} (v{})'.format(graph.name, graph.version),
            time='{:.2f}'.format(time.time() - t)
        )

    log.info('Added synchronous validator to %s', app)
