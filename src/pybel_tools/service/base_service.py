# -*- coding: utf-8 -*-


class BaseService:
    """The base service class provides a functional interface that all PyBEL services must implement"""

    def __init__(self, manager):
        """
        :param manager: A cache manager
        :type manager: pybel.manager.cache.CacheManager
        """
        self.manager = manager
