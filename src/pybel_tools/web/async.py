# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import codecs
import logging

from celery.utils.log import get_task_logger
from flask import render_template, flash, redirect, url_for, jsonify
from flask_login import current_user

from pybel import from_lines
from pybel.manager import build_manager
from .forms import CompileForm
from ..mutation.metadata import add_canonical_names
import os
celery_log = get_task_logger(__name__)
log = logging.getLogger(__name__)


def build_celery_app(app, manager):
    """
    
    :param flask.Flask app: 
    :param pybel.manager.cache.CacheManager manager: 
    :return: 
    """
    from celery import Celery

    celery_app = Celery(app.name, broker='amqp://localhost')

    @celery_app.task
    def add(x, y):
        return x, y

    @celery_app.task(name='async-compile')
    def do_async_compile(lines, connection):
        m = build_manager(connection)
        graph = from_lines(
            lines,
            manager=m,
        )

        with open(os.path.expanduser('~/Desktop/status.txt'), 'w') as f:
            print('done', file=f)

        add_canonical_names(graph)
        network = m.insert_graph(graph, store_parts=False)
        return network.id

    @app.route('/asynccompile', methods=['GET', 'POST'])
    def view_async_compile():
        form = CompileForm(save_network=True)

        if not form.validate_on_submit():
            return render_template('compile.html', form=form, current_user=current_user)

        lines = codecs.iterdecode(form.file.data.stream, form.encoding.data)
        lines = list(lines)

        task = do_async_compile.delay(lines, manager.connection)

        flash('Queued compilation task {}'.format(task))

        return redirect(url_for('view_networks'))

    @app.route('/status/<task_id>')
    def taskstatus(task_id):
        task = do_async_compile.AsyncResult(task_id)
        if task.state == 'PENDING':
            response = {
                'state': task.state,
                'current': 0,
                'total': 1,
                'status': 'Pending...'
            }
        elif task.state != 'FAILURE':
            response = {
                'state': task.state,
                'current': task.info.get('current', 0),
                'total': task.info.get('total', 1),
                'status': task.info.get('status', '')
            }
            if 'result' in task.info:
                response['result'] = task.info['result']
        else:
            # something went wrong in the background job
            response = {
                'state': task.state,
                'current': 1,
                'total': 1,
                'status': str(task.info),  # this is the exception raised
            }
        return jsonify(response)

    log.info('build async compiler app')

    return celery_app
