# -*- coding: utf-8 -*-

"""
This module contains all of the services necessary through the PyBEL API Definition, backed by the PyBEL cache manager.
"""

# from .base_service import PybelService
from flask import Flask

from .db_service_utils import DatabaseService

# class DatabaseService(PybelService):#

#    def __init__(self):
#        pass

DATABASE_SERVICE = 'database_service'


def build_database_service_app(dsa):
    """Builds the PyBEL Dictionary-Backed API Service. Adds a latent PyBEL Dictionary service that can be retrieved
    with :func:`get_dict_service`

    :param dsa: A Flask App
    :type dsa: Flask
    """

    api = DatabaseService()
    dsa.config[DATABASE_SERVICE] = api

    @dsa.route('/networks')
    def list_networks():
        pass

    @dsa.route('/namespaces')
    def func():
        pass

    @dsa.route('/namespaces/by_network/<int:network_id>', methods=['GET'])
    def func():
        pass

    @dsa.route('/names/<str:definition_key>', methods=['GET'])
    def func():
        pass


app = Flask(__name__)
build_database_service_app(app)
