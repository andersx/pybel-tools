# -*- coding: utf-8 -*-

from pybel.constants import PYBEL_CONNECTION
from pybel.manager import build_manager
from pybel.manager.models import Base
from .dict_service_utils import DictionaryService


class _FlaskPybelState:
    def __init__(self, manager):
        self.manager = build_manager(manager)
        self.api = DictionaryService(manager=self.manager)


class FlaskPybel:
    """Encapsulates the data needed for the PyBEL Web Application"""

    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """
        :param flask.Flask app: 
        """
        app.config.setdefault(PYBEL_CONNECTION, None)

        manager = build_manager(app.config.get(PYBEL_CONNECTION))

        Base.metadata.bind = manager.engine
        Base.query = manager.session.query_property()

        app.extensions['pybel'] = _FlaskPybelState(manager)


def get_state(app):
    """
    :param flask.Flask app: 
    :rtype: _FlaskPybelState
    """
    if 'pybel' not in app.extensions:
        raise ValueError

    return app.extensions['pybel']


def get_manager(app):
    """
    :param flask.Flask app: 
    :rtype: pybel.manager.cache.CacheManager
    """
    return get_state(app).manager


def get_api(app):
    """
    :param flask.Flask app: 
    :rtype: DictionaryService
    """
    return get_state(app).api
