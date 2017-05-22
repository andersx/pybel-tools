# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import codecs
import logging

from flask import render_template, current_app, Blueprint, flash
from flask_login import current_user

from pybel.constants import PYBEL_CONNECTION
from .celery import create_celery
from .forms import CompileForm

log = logging.getLogger(__name__)

async_blueprint = Blueprint('async_compiler', __name__)


@async_blueprint.route('/asynccompile', methods=['GET', 'POST'])
def view_async_compile():
    """Renders the compiler form for asynchronous compilation"""
    form = CompileForm(save_network=True)

    if not form.validate_on_submit():
        flash('Using asynchronous compilation service. This service is currently in beta.', category='danger')
        return render_template('compile.html', form=form, current_user=current_user)

    lines = codecs.iterdecode(form.file.data.stream, form.encoding.data)
    lines = list(lines)

    celery = create_celery(current_app)
    task = celery.send_task('pybelcompile', args=(lines, current_app.config.get(PYBEL_CONNECTION)))

    flash('Queued compilation task {}.'.format(task))

    return render_template('compile_status.html', task=task)
