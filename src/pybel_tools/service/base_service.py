# -*- coding: utf-8 -*-

from pybel.manager.cache import build_manager


class BaseService:
    """The base service class provides a functional interface that all PyBEL services must implement"""

    def __init__(self, connection=None):
        """
        :param connection: The database connection string. Default location described in
                           :code:`pybel.manager.cache.BaseCacheManager`
        :type connection: str
        """
        self.manager = build_manager(connection=connection)
