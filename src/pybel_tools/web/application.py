# -*- coding: utf-8 -*-

import logging
import os
import socket
import time
from getpass import getuser

import flask
from flask import Flask
from flask_bootstrap import Bootstrap
from flask_mail import Mail, Message

from pybel.constants import config as pybel_config
from .async_parser_service import async_blueprint
from .extension import FlaskPybel

log = logging.getLogger(__name__)

bootstrap_extension = Bootstrap()
pybel_extension = FlaskPybel()
mail = Mail()


def create_application(get_mail=False, **kwargs):
    """Builds a Flask app for the PyBEL web service
    
    1. Loads default config
    2. Updates with kwargs
    
    :param dict kwargs: keyword arguments to add to config
    :rtype: flask.Flask
    """
    app = Flask(__name__)

    app.config.from_object('pybel_tools.web.config.Config')

    if 'PYBEL_WEB_CONFIG' in os.environ:
        env_conf_path = os.environ['PYBEL_WEB_CONFIG']
        if not os.path.exists(env_conf_path):
            log.warning('configuration from environment at %s does not exist', os.environ['PYBEL_WEB_CONFIG'])
        else:
            log.info('importing config from %s', os.environ['PYBEL_WEB_CONFIG'])
            app.config.from_json(os.path.expanduser(os.environ['PYBEL_WEB_CONFIG']))

    app.config.update(pybel_config)
    app.config.update(kwargs)

    # Initialize extensions
    bootstrap_extension.init_app(app)

    if app.config.get('MAIL_SERVER'):
        mail.init_app(app)

        if app.config.get('PYBEL_WEB_STARTUP_NOTIFY'):
            startup_message = Message(
                subject="PyBEL Web - Startup",
                body="PyBEL Web was started on {} by {} at {}".format(socket.gethostname(), getuser(), time.asctime()),
                sender=("PyBEL Web", 'pybel@scai.fraunhofer.de'),
                recipients=[app.config.get('PYBEL_WEB_STARTUP_NOTIFY')]
            )
            with app.app_context():
                mail.send(startup_message)

    pybel_extension.init_app(app)

    app.register_blueprint(async_blueprint)

    if not get_mail:
        return app

    return app, mail
