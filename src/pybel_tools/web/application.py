# -*- coding: utf-8 -*-

import logging

import flask
from flask import Flask
from flask_bootstrap import Bootstrap

from .async import async_blueprint
from .extension import FlaskPybel

log = logging.getLogger(__name__)

bootstrap_extension = Bootstrap()
pybel_extension = FlaskPybel()


def create_application(config=None):
    """Builds a Flask app for the PyBEL web service

    :rtype: flask.Flask
    """
    app = Flask(__name__)

    # get config?
    app.config.update({
        'CELERY_BROKER_URL': 'amqp://localhost',
    })

    if config is not None:
        app.config.update(config)

    # Initialize extensions
    bootstrap_extension.init_app(app)
    pybel_extension.init_app(app)

    app.register_blueprint(async_blueprint)

    return app
