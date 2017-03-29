# -*- coding: utf-8 -*-

"""
This module contains all of the services necessary through the PyBEL API Definition, backed by the PyBEL cache manager.
"""
from pybel.manager.cache import CacheManager
from pybel.manager.graph_cache import GraphCacheManager

from .base_service import PybelService


class DatabaseService(PybelService):
    def __init__(self):
        self.cm = CacheManager()
        self.gcm = GraphCacheManager()

    def get_networks(self):
        pass

    def get_namespaces(self, network_id=None, **kwargs):
        """

        :param network_id: Network id in the relational database.
        :type network_id: int
        :param \**kwargs: See below.

        :Keyword Arguments:
        * *name_list* (``bool``) --
          Flag that indicates if a names list is required.
        * *namespace_key* (``str``) --
          Keyword that identifies the namespace of which the names should be shown. Only valid in combination with
          :code:`name_list = True`.

        :return: List of dictionaries that describe all namespaces.
        """
        namespaces = self.cm.ls_namespaces(data=True)

        if network_id:
            pass

        return namespaces

    def get_annotations(self, **kwargs):
        pass

    def get_citations(self, **kwargs):
        pass

    def get_edges(self, network_id=None, pmid_id=None, statement=None, source=None, target=None, relation=None,
                  author=None, citation=None, annotations=None):

        if author and citation is None and pmid_id is None:
            citation = self.gcm.query_citation(author=author)

        elif pmid_id:
            citation = str(pmid_id)

        edges = self.gcm.query_edge(bel=statement, source=source, target=target, relation=relation, citation=citation,
                                    annotation=annotations)

    def get_nodes(self, **kwargs):
        pass

    def get_paths(self, **kwargs):
        pass
