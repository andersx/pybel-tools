# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import codecs
import logging

from flask import render_template, current_app, Blueprint, flash
from flask_login import current_user

from pybel.constants import PYBEL_CONNECTION
from .celery import create_celery
from .forms import ParserForm

log = logging.getLogger(__name__)

async_blueprint = Blueprint('async_parser', __name__)


@async_blueprint.route('/asyncparser', methods=['GET', 'POST'])
def view_async_parser():
    """Renders the parser form for asynchronous parsing"""
    form = ParserForm(save_network=True)

    if not form.validate_on_submit():
        flash('Using asynchronous parser service. This service is currently in beta.', category='danger')
        return render_template('parser.html', form=form, current_user=current_user)

    lines = codecs.iterdecode(form.file.data.stream, form.encoding.data)
    lines = list(lines)

    celery = create_celery(current_app)
    task = celery.send_task('pybelparser', args=(lines, current_app.config.get(PYBEL_CONNECTION)))

    flash('Queued parsing task {}.'.format(task))

    return render_template('parser_status.html', task=task)
