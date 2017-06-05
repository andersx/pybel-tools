# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import logging

from flask import flash, redirect, url_for
from flask import render_template, Blueprint
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from werkzeug.local import LocalProxy

from pybel import from_bytes
from .constants import integrity_message
from .forms import UploadForm
from .models import add_network_reporting
from .utils import get_current_manager

log = logging.getLogger(__name__)

upload_blueprint = Blueprint('upload', __name__)
manager = LocalProxy(get_current_manager)


@upload_blueprint.route('/upload', methods=['GET', 'POST'])
@login_required
def view_upload():
    """An upload form for a BEL script"""
    form = UploadForm()

    if not form.validate_on_submit():
        return render_template('upload.html', form=form, current_user=current_user)

    log.info('uploading %s', form.file.data.filename)

    try:
        graph_bytes = form.file.data.read()
        graph = from_bytes(graph_bytes)
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
        add_network_reporting(
            manager,
            network,
            current_user,
            graph.number_of_nodes(),
            graph.number_of_edges(),
            len(graph.warnings),
            preparsed=True,
            public=form.public.data
        )
    except IntegrityError:
        log.exception('integrity error')
        flash('problem with reporting service', category='warning')
        manager.rollback()

    return redirect(url_for('view_summary', graph_id=network.id))
