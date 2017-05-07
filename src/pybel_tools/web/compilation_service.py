# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import codecs
import logging
import time
import traceback

import requests
from flask import render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from pybel import from_lines
from pybel.parser.parse_exceptions import InconsistientDefinitionError
from .constants import integrity_message, reporting_log
from .forms import CompileForm
from .utils import render_graph_summary
from ..mutation.metadata import add_canonical_names

log = logging.getLogger(__name__)


def render_error(exception):
    """Displays an error in compilation/uploading"""
    traceback_lines = traceback.format_exc().split('\n')
    return render_template('parse_error.html', error_text=str(exception), traceback_lines=traceback_lines)


def build_synchronous_compiler_service(app, manager, enable_cache=True):
    """Adds the endpoints for a synchronous web validation web app

    :param flask.Flask app: A Flask application
    :param manager: A PyBEL cache manager
    :type manager: pybel.manager.cache.CacheManager
    :param enable_cache: Should the user be given the option to cache graphs?
    :type enable_cache: bool
    """

    @app.route('/compile', methods=['GET', 'POST'])
    @login_required
    def view_compile():
        """An upload form for a BEL script"""
        form = CompileForm(save_network=True)

        if not form.validate_on_submit():
            return render_template('compile.html', form=form, current_user=current_user)

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
            flash("Resource doesn't exist.", category='error')
            return render_error(e)
        except InconsistientDefinitionError as e:
            flash('{} was defined multiple times.'.format(e.definition), category='error')
            return redirect(url_for('view_compile'))
        except Exception as e:
            flash('Compilation error: {}'.format(e))
            return redirect(url_for('view_compile'))

        if not enable_cache:
            flash('Sorry, graph storage is not currently enabled.', category='warning')
            return render_graph_summary(0, graph)

        if not form.save_network.data and not form.save_edge_store.data:
            return render_graph_summary(0, graph)

        try:
            network = manager.insert_graph(graph, store_parts=form.save_edge_store.data)
        except IntegrityError as e:
            flash(integrity_message.format(graph.name, graph.version), category='error')
            manager.rollback()
            return redirect(url_for('view_compile'))
        except Exception as e:
            flash("Error storing in database: {}".format(e), category='error')
            log.exception('general storage error')
            return redirect(url_for('view_compile'))

        log.info('done storing %s [%d]', form.file.data.filename, network.id)
        reporting_log.info('%s (%s) compiled %s v%s with %d nodes, %d edges, and %d warnings)', current_user.name,
                           current_user.username, graph.name, graph.version, graph.number_of_nodes(),
                           graph.number_of_edges(), len(graph.warnings))

        return redirect(url_for('view_summary', graph_id=network.id))

    log.info('Added synchronous compiler to %s', app)
