# -*- coding: utf-8 -*-

import logging
import os

import flask
from flask import Flask
from flask_bootstrap import Bootstrap

from .async_compilation_service import async_blueprint
from .extension import FlaskPybel

log = logging.getLogger(__name__)

bootstrap_extension = Bootstrap()
pybel_extension = FlaskPybel()


def create_application(**kwargs):
    """Builds a Flask app for the PyBEL web service
    
    1. Loads default config
    2. Updates with kwargs

    :rtype: flask.Flask
    """
    app = Flask(__name__)

    app.config.from_object('pybel_tools.web.config.Config')

    if 'PYBEL_WEB_CONFIG' in os.environ:
        log.info('importing config from %s', os.environ['PYBEL_WEB_CONFIG'])
        app.config.from_json(os.environ['PYBEL_WEB_CONFIG'])

    app.config.update(kwargs)

    # Initialize extensions
    bootstrap_extension.init_app(app)
    pybel_extension.init_app(app)

    app.register_blueprint(async_blueprint)

    return app
