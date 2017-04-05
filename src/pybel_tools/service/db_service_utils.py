# -*- coding: utf-8 -*-

"""
This module contains all of the services necessary through the PyBEL API Definition, backed by the PyBEL cache manager.
"""
from pybel.manager.cache import CacheManager
from pybel.manager.graph_cache import GraphCacheManager

from .base_service import PybelService


class DatabaseService(PybelService):
    def __init__(self, mySQLConnection):
        self.cm = CacheManager(mySQLConnection)
        self.gcm = GraphCacheManager(mySQLConnection)

    def get_networks(self):
        """Provides a list of all networks stored in the PyBEL database.

        :return: A list of all networks in the PyBEL database.
        :rtype: list
        """

        network_ls = self.gcm.query_network(as_dict_list=True)
        return [(n['id'], n['name'], n['version']) for n in network_ls]

    def get_namespaces(self, network_id=None, offset_start=0, offset_end=500, **kwargs):
        """Provides a list of namespaces filtered by the given parameters.

        :param network_id: Primary identifier of the network in the PyBEL database. This can be obtained with the
                           get_networks function.
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
        result = []

        if network_id:
            network = self.gcm.query_network(db_id=network_id)[0]
            result = [namespace.data for namespace in network.namespaces[offset_start:offset_end]]

        if 'name_list' in kwargs:
            if kwargs['name_list'] == True and 'namespace_key' in kwargs:
                keyword_url_dict = self.cm.get_namespace_urls(keyword_url_dict=True)
                namespace_url = keyword_url_dict[kwargs['namespace_key']]
                self.cm.ensure_namespace(url=namespace_url)
                namespace_data = self.cm.get_namespace_data(url=namespace_url)

                result = {
                    'namespace_definition': namespace_data,
                    'names': self.cm.namespace_cache[namespace_url]
                }

        if len(result) == 0:
            result = self.cm.get_namespace_data()

        return result

    def get_annotations(self, network_id=None, offset_start=0, offset_end=500, **kwargs):
        """Provides a list of annotations filtered by the given parameters.

        :param network_id: Primary identifier of the network in the PyBEL database. This can be obtained with the
                           get_networks function.
        :type network_id: int
        :param \**kwargs: See below.

        :Keyword Arguments:
        * *name_list* (``bool``) --
          Flag that indicates if a annotations list is required.
        * *annotation_key* (``str``) --
          Keyword that identifies the annotation definition of which the annotations should be shown.
          Only valid in combination with :code:`name_list = True`.

        :return: List of dictionaries that describe all namespaces.
        """
        result = []

        if network_id:
            network = self.gcm.query_network(db_id=network_id)
            result = [annotation.data for annotation in network.annotations]

        if 'name_list' in kwargs:
            if kwargs['name_list'] == True and 'annotation_key' in kwargs:
                keyword_url_dict = self.cm.get_annotation_urls(keyword_url_dict=True)
                annotation_url = keyword_url_dict[kwargs['annotation_key']]
                self.cm.ensure_annotation(url=annotation_url)
                annotation_data = self.cm.get_annotation_data(url=annotation_url)

                result = {
                    'annotation_definition': annotation_data,
                    'annotations': self.cm.annotation_cache[annotation_url]
                }

        if len(result) == 0:
            result = self.cm.get_annotation_data()

        return result

    def get_citations(self, network_id=None, author=None, offset_start=0, offset_end=500):
        """

        :param network_id: Primary identifier of the network in the PyBEL database. This can be obtained with the
                           get_networks function.
        :type network_id: int
        :param author: The name of an author that participated in creation of the citation.
        :type author: str
        :return:
        """
        result = []

        if network_id:
            network = self.gcm.query_network(db_id=network_id)[0]
            result = [citation.data for citation in network.citations]

        if author:
            result = self.gcm.query_citation(author=author, as_dict_list=True)

        if len(result) == 0:
            result = self.gcm.query_citation(as_dict_list=True)

        return result

    def get_edges(self, network_id=None, pmid_id=None, statement=None, source=None, target=None, relation=None,
                  author=None, citation=None, annotations=None, offset_start=0, offset_end=500):
        """Provides a list of edges (nanopubs) filtered by the given parameters.

        :param network_id: Primary identifier of the network in the PyBEL database. This can be obtained with the
                           get_networks function.
        :type network_id: int
        :param pmid_id: Pubmed identifier of a specific citation.
        :type pmid_id: str
        :param statement: A BEL statement that represents the needed edge.
        :type statement: str
        :param source: A BEL term that describes the SUBJECT of the seeked relation.
        :type source: str
        :param target: A BEL term that describes the OBJECT of the seeked relation.
        :type target: str
        :param relation: The relation that is used in the seeked relationship.
        :type relation: str
        :param author: An author that participated to the cited article.
        :type author: str
        :param citation: A citation that is used to back up the given relationship.
        :type citation: str or pybel.models.Citation
        :param annotations: A dictionary that describes an annotation that is the context of the seeked relationship.
        :type annotations: dict
        :return:
        """

        result = []

        if network_id:
            network = self.gcm.query_network(db_id=network_id)[0]

            result = {
                'network': network.data,
                'offset': {
                    'start': offset_start,
                    'end': offset_end
                }
            }
            if offset_start > 0:
                offset_start = offset_start - 1
            if offset_start == offset_end:
                offset_end = offset_end + 1

            result['edges'] = [edge.data_min for edge in network.edges[offset_start:offset_end]]


        if author and citation is None and pmid_id is None:
            citation = self.gcm.query_citation(author=author)

        elif pmid_id:
            citation = str(pmid_id)

        if len(result) == 0:
            edges = self.gcm.query_edge(bel=statement, source=source, target=target,
                                        relation=relation, citation=citation, annotation=annotations)

            result_edges = {
                'number_of_edges': len(edges),
                'edges': [edge.data_min for edge in edges],
            }

        return result

    def get_nodes(self, network_id=None, db_id=None, bel=None, namespace=None, name=None, offset_start=0,
                  offset_end=500):
        """Provides a list of nodes filtered by the given parameters.

        :param network_id: Primary identifier of the network in the PyBEL database. This can be obtained with the
                           get_networks function.
        :type network_id: int
        :param bel: A BEL term that describes the seeked node.
        :type bel: str
        :param namespace: A namespace keyword (e.g. HGNC) that represents a namespace that describes the nodes name.
        :type namespace: str
        :param name: The name of the node (biological entity).
        :type name: str
        :return:
        """
        if db_id:
            result = self.gcm.query_node(db_id=db_id)
        elif network_id:
            network = self.gcm.query_network(db_id=network_id)
            result = [node.data for node in network.nodes[offset_start:offset_end]]
        else:
            result = self.gcm.query_node(bel=bel, namespace=namespace, name=name, as_dict_list=True)

        return result

    def get_paths(self, **kwargs):
        pass
