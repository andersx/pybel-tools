# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import codecs
import logging
import time

import requests
from flask import render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from pybel import from_lines
from pybel.parser.parse_exceptions import InconsistientDefinitionError
from .constants import integrity_message
from .extension import get_manager
from .forms import ParserForm
from .models import add_network_reporting, log_graph
from .utils import render_graph_summary
from ..mutation.metadata import add_canonical_names

log = logging.getLogger(__name__)


def build_synchronous_parser_service(app):
    """Adds the endpoints for a synchronous web validation web app

    :param flask.Flask app: A Flask application
    """
    manager = get_manager(app)

    @app.route('/parser', methods=['GET', 'POST'])
    @login_required
    def view_parser():
        """An upload form for a BEL script"""
        form = ParserForm(save_network=True)

        if not form.validate_on_submit():
            return render_template('parser.html', form=form, current_user=current_user)

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
            message = "Resource doesn't exist."
            flash(message, category='error')
            return redirect(url_for('view_parser'))
        except InconsistientDefinitionError as e:
            log.error('%s was defined multiple times', e.definition)
            flash('{} was defined multiple times.'.format(e.definition), category='error')
            return redirect(url_for('view_parser'))
        except Exception as e:
            log.exception('parser error')
            flash('Compilation error: {}'.format(e))
            return redirect(url_for('view_parser'))

        if app.config.get('PYBEL_WEB_DISABLE_CACHE'):
            flash('Sorry, graph storage is not currently enabled.', category='warning')
            log_graph(graph, current_user, preparsed=False)
            return render_graph_summary(0, graph)

        if not form.save_network.data and not form.save_edge_store.data:
            log_graph(graph, current_user, preparsed=False)
            return render_graph_summary(0, graph)

        try:
            network = manager.insert_graph(graph, store_parts=form.save_edge_store.data)
        except IntegrityError:
            log_graph(graph, current_user, preparsed=False, failed=True)
            log.exception('integrity error')
            flash(integrity_message.format(graph.name, graph.version), category='error')
            manager.rollback()
            return redirect(url_for('view_parser'))
        except Exception as e:
            log_graph(graph, current_user, preparsed=False, failed=True)
            log.exception('general storage error')
            flash("Error storing in database: {}".format(e), category='error')
            return redirect(url_for('view_parser'))

        log.info('done storing %s [%d]', form.file.data.filename, network.id)

        try:
            add_network_reporting(
                manager,
                network,
                current_user,
                graph.number_of_nodes(),
                graph.number_of_edges(),
                len(graph.warnings),
                preparsed=False,
                public=form.public.data
            )
        except IntegrityError:
            log.exception('integrity error')
            flash('problem with reporting service', category='warning')
            manager.rollback()

        return redirect(url_for('view_summary', graph_id=network.id))

    log.info('Added synchronous parser to %s', app)
