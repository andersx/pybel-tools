# -*- coding: utf-8 -*-

import logging

from flask import redirect, url_for, request
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView as ModelViewBase
from flask_admin import AdminIndexView
from flask_security import current_user

from pybel.manager.models import Network, Namespace, Annotation
from .extension import get_manager
from .models import Report, Experiment
from .security import User, Role

log = logging.getLogger(__name__)


class ModelView(ModelViewBase):
    """Adds plugin for Flask-Security to Flask-Admin model views"""

    def is_accessible(self):
        """Checks the current user is an admin"""
        return current_user.is_authenticated and current_user.admin

    def inaccessible_callback(self, name, **kwargs):
        """redirect to login page if user doesn't have access"""
        return redirect(url_for('login', next=request.url))


def build_admin_service(app):
    """Adds Flask-Admin database front-end
    
    :param flask.Flask app: A PyBEL web app 
    """
    manager = get_manager(app)
    admin = Admin(app, template_mode='bootstrap3')
    admin.add_view(ModelView(User, manager.session))
    admin.add_view(ModelView(Role, manager.session))
    admin.add_view(ModelView(Namespace, manager.session))
    admin.add_view(ModelView(Annotation, manager.session))
    admin.add_view(ModelView(Network, manager.session))
    admin.add_view(ModelView(Report, manager.session))
    admin.add_view(ModelView(Experiment, manager.session))

    log.info('done building admin service for %s', app)
