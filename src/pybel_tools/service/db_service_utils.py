# -*- coding: utf-8 -*-

"""
This module contains all of the services necessary through the PyBEL API Definition, backed by the PyBEL cache manager.
"""

from pybel.manager.cache import build_manager

from .base_service import PybelService


class DatabaseService(PybelService):
    """Provides queries to access data stored in the PyBEL edge store"""

    def __init__(self, connection=None):
        """
        :param connection: custom database connection string
        :type connection: str
        """
        self.manager = build_manager(connection=connection)

    def get_networks(self):
        """Provides a list of all networks stored in the PyBEL database.

        :return: A list of all networks in the PyBEL database.
        :rtype: list
        """

        network_ls = self.manager.get_network(as_dict_list=True)
        return [(n['id'], n['name'], n['version']) for n in network_ls]

    def get_namespaces(self, network_id=None, offset_start=0, offset_end=500, name_list=False, keyword=None):
        """Provides a list of namespaces filtered by the given parameters.

        :param network_id: Primary identifier of the network in the PyBEL database. This can be obtained with the
                           get_networks function.
        :type network_id: int
        :param offset_start: The startingpoint of the offset (position in database)
        :type offset_start: int
        :param offset_end: The end point of the offset (position in database)
        :type offset_end: int
        :param name_list: Flag that identifies if a list of all names in a namespace should be created.
        :type name_list: bool
        :param keyword: The keyword used to identify a specific namespace. This is only used if name_list is True.
        :type keyword: str

        :return: List of dictionaries that describe all namespaces.
        """
        result = []

        if network_id:
            network = self.manager.get_network(network_id=network_id)[0]
            result = [namespace.data for namespace in network.namespaces[offset_start:offset_end]]

        if name_list and keyword:
            keyword_url_dict = self.manager.get_namespace_urls(keyword_url_dict=True)
            namespace_url = keyword_url_dict[keyword]
            self.manager.ensure_namespace(url=namespace_url)
            namespace_data = self.manager.get_namespace_data(url=namespace_url)

            result = {
                'namespace_definition': namespace_data,
                'names': self.manager.namespace_cache[namespace_url]
            }

        if not result:
            result = self.manager.get_namespace_data()

        return result

    def get_annotations(self, network_id=None, offset_start=0, offset_end=500, name_list=False, keyword=None):
        """Provides a list of annotations filtered by the given parameters.

        :param network_id: Primary identifier of the network in the PyBEL database. This can be obtained with the
                           get_networks function.
        :type network_id: int
        :param offset_start: The startingpoint of the offset (position in database)
        :type offset_start: int
        :param offset_end: The end point of the offset (position in database)
        :type offset_end: int
        :param name_list: Flag that identifies if a list of all names in a namespace should be created.
        :type name_list: bool
        :param keyword: The keyword used to identify a specific namespace. This is only used if name_list is True.
        :type keyword: str

        :return: List of dictionaries that describe all namespaces.
        """
        result = []

        if network_id:
            network = self.manager.get_network(network_id=network_id)[0]
            result = [annotation.data for annotation in network.annotations[offset_start:offset_end]]

        if name_list:
            if name_list and keyword:
                keyword_url_dict = self.manager.get_annotation_urls(keyword_url_dict=True)
                annotation_url = keyword_url_dict[keyword]
                self.manager.ensure_annotation(url=annotation_url)
                annotation_data = self.manager.get_annotation_data(url=annotation_url)

                result = {
                    'annotation_definition': annotation_data,
                    'annotations': self.manager.annotation_cache[annotation_url]
                }

        if len(result) == 0:
            result = self.manager.get_annotation_data()

        return result

    def get_citations(self, network_id=None, author=None, offset_start=0, offset_end=500):
        """

        :param network_id: Primary identifier of the network in the PyBEL database. This can be obtained with the
                           get_networks function.
        :type network_id: int
        :param author: The name of an author that participated in creation of the citation.
        :type author: str
        :param offset_start: The starting point of the offset (position in database)
        :type offset_start: int
        :param offset_end: The end point of the offset (position in database)
        :type offset_end: int
        :return:
        """
        result = []

        if network_id:
            network = self.manager.get_network(network_id=network_id)[0]
            result = [citation.data for citation in network.citations[offset_start:offset_end]]

        if author:
            result = self.manager.get_citation(author=author, as_dict_list=True)

        if len(result) == 0:
            result = self.manager.get_citation(as_dict_list=True)

        return result

    def get_edges(self, network_id=None, pmid=None, statement=None, source=None, target=None, relation=None,
                  author=None, citation=None, annotations=None, offset_start=0, offset_end=500):
        """Provides a list of edges (nanopubs) filtered by the given parameters.

        :param network_id: Primary identifier of the network in the PyBEL database. This can be obtained with the
                           get_networks function.
        :type network_id: int
        :param pmid: Pubmed identifier of a specific citation.
        :type pmid: str
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
        :param offset_start: The starting point of the offset (position in database)
        :type offset_start: int
        :param offset_end: The end point of the offset (position in database)
        :type offset_end: int
        :return:
        :rtype:
        """
        if network_id:
            network = self.manager.get_network(network_id=network_id)[0]

            result = {
                'network': network.data,
                'offset': {
                    'start': offset_start,
                    'end': offset_end
                }
            }
            if offset_start > 0:
                offset_start -= 1
            if offset_start == offset_end:
                offset_end += 1

            result['edges'] = [edge.data_min for edge in network.edges[offset_start:offset_end]]
            result['number_of_edges'] = len(result['edges'])
            return result

        if author and citation is None and pmid is None:
            citation = self.manager.get_citation(author=author)

        elif pmid:
            citation = str(pmid)

        edges = self.manager.get_edge(bel=statement, source=source, target=target,
                                      relation=relation, citation=citation, annotation=annotations)

        result = {
            'number_of_edges': len(edges),
            'edges': [edge.data_min for edge in edges],
        }

        return result

    def get_nodes(self, network_id=None, node_id=None, bel=None, namespace=None, name=None, offset_start=0,
                  offset_end=500):
        """Provides a list of nodes filtered by the given parameters.

        :param network_id: Primary identifier of the network in the PyBEL database. This can be obtained with the
                           :func:`get_networks` function.
        :type network_id: int
        :param node_id: A node's database identifier
        :type node_id: int
        :param bel: A BEL term that describes the seeked node.
        :type bel: str
        :param namespace: A namespace keyword (e.g. HGNC) that represents a namespace that describes the nodes name.
        :type namespace: str
        :param name: The name of the node (biological entity).
        :type name: str
        :param offset_start: The starting point of the offset (position in database)
        :type offset_start: int
        :param offset_end: The end point of the offset (position in database)
        :type offset_end: int
        :return:
        :rtype:
        """
        if node_id:
            result = self.manager.get_node(node_id=node_id)
        elif network_id:
            network = self.manager.get_network(network_id=network_id)[0]
            result = [node.data for node in network.nodes[offset_start:offset_end]]
        else:
            result = self.manager.get_node(bel=bel, namespace=namespace, name=name, as_dict_list=True)

        return result
