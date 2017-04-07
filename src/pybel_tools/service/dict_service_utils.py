# -*- coding: utf-8 -*-

"""
This module contains all of the services necessary through the PyBEL API Definition, backed by a network
dictionary
"""

import logging
from collections import Counter

import networkx as nx

from pybel import from_bytes, BELGraph
from pybel.constants import *
from pybel.manager.models import Network
from pybel.utils import hash_tuple
from .base_service import BaseService
from ..constants import CNAME
from ..mutation import add_canonical_names, left_merge
from ..mutation.metadata import parse_authors
from ..selection import get_filtered_subgraph
from ..summary import get_authors, get_pmids
from ..utils import citation_to_tuple

log = logging.getLogger(__name__)


def _node_to_identifier(node, graph):
    return hash_tuple(graph.nodes[node])


class DictionaryService(BaseService):
    """The dictionary service contains functions that implement the PyBEL API with a in-memory backend using 
    dictionaries.
    """

    def __init__(self, connection=None):
        """
        :param connection: The database connection string. Default location described in
                           :code:`pybel.manager.cache.BaseCacheManager`
        :type connection: str
        """
        super(DictionaryService, self).__init__(connection=connection)

        #: dictionary of {int id: BELGraph graph}
        self.networks = {}

        #: dictionary of {tuple node: int id}
        self.node_nid = {}

        #: dictionary of {int id: tuple node}
        self.nid_node = {}

        self.full_network = BELGraph()
        self.full_network_loaded = False

    def _validate_network_id(self, network_id):
        if network_id not in self.networks:
            raise ValueError()

    def _build_edge_json(self, graph, u, v, d):
        """

        :param graph:
        :type graph: pybel.BELGraph
        :param u:
        :param v:
        :param d:
        :return:
        """
        return {
            'source': graph.node[u] + {'id': self.node_nid[u]},
            'target': graph.node[v] + {'id': self.node_nid[v]},
            'data': d
        }

    def add_network(self, network_id, graph):
        """Adds a network to the module-level cache from the underlying database

        :param network_id: The database identifier for the network
        :type network_id: int
        :param graph: A BEL Graph
        :type graph: pybel.BELGraph
        """
        if network_id in self.networks:
            return

        add_canonical_names(graph)

        self.networks[network_id] = graph
        self.update_node_indexes(graph)

        log.info('loaded network: [%s] %s ', network_id, graph.document.get(METADATA_NAME, 'UNNAMED'))

    def load_networks(self, check_version=True):
        """This function needs to get all networks from the graph cache manager and make a dictionary

        :param check_version: Should the version of the BELGraphs be checked from the database? Defaults to :code`True`.
        :type check_version: bool
        """
        for network_id, blob in self.manager.session.query(Network.id, Network.blob).all():
            graph = from_bytes(blob, check_version=check_version)
            self.add_network(network_id, graph)

    def update_node_indexes(self, graph):
        """Updates identifiers for nodes based on addition order

        :param graph: A BEL Graph
        :type graph: pybel.BELGraph
        """
        for node in graph.nodes_iter():
            if node in self.node_nid:
                continue

            self.node_nid[node] = len(self.node_nid)
            self.nid_node[self.node_nid[node]] = node

    # Graph mutation functions

    def relabel_nodes_to_identifiers(self, graph):
        """Relabels all nodes by their identifiers, in place. This function is a thin wrapper around
        :code:`relabel.relabel_nodes` with the module level variable :code:`node_id` used as the mapping.

        :param graph: A BEL Graph
        :type graph: pybel.BELGraph
        """
        mapping = {k: v for k, v in self.node_nid.items() if k in graph}
        nx.relabel.relabel_nodes(graph, mapping, copy=False)

    # Graph selection functions

    def get_network_ids(self):
        """Returns a list of all network IDs

        :rtype: list of int
        """
        return list(self.networks)

    def get_network_by_id(self, network_id):
        """Gets a network by its ID

        :param network_id: The internal ID of the network to get
        :type network_id: int
        :return: A BEL Graph
        :rtype: BELGraph
        """
        return self.networks[network_id]

    def get_super_network(self, force=False):
        """Gets all networks and merges them together. Caches in self.full_network.

        :return: A BEL Graph
        :rtype: pybel.BELGraph
        """

        if not force and self.full_network_loaded:
            return self.full_network

        for network_id in self.get_network_ids():
            left_merge(self.full_network, self.get_network_by_id(network_id))

        parse_authors(self.full_network)

        log.info('Loaded super network')
        self.full_network_loaded = True

        return self.full_network

    def get_node_by_id(self, node_id):
        """Returns the node tuple based on the node id

        :param node_id: The node's id
        :type node_id: int or str
        :return: the node tuple
        :rtype: tuple
        """
        if isinstance(node_id, str):
            return self.nid_node[int(node_id)]
        elif isinstance(node_id, int):
            return self.nid_node[node_id]

        raise TypeError('{} is wrong type'.format(node_id))

    def get_namespaces_in_network(self, network_id):
        """Returns the namespaces in a given network

        :param network_id: The internal ID of the network to get
        :type network_id: int
        :return:
        """
        return list(self.get_network_by_id(network_id).namespace_url.values())

    def get_annotations_in_network(self, network_id):
        return list(self.get_network_by_id(network_id).annotation_url.values())

    def get_citations_in_network(self, network_id):
        g = self.get_network_by_id(network_id)
        citations = set(data[CITATION] for _, _, data in g.edges_iter(data=True))
        return list(sorted(citations, key=citation_to_tuple))

    def get_edges_in_network(self, network_id):
        g = self.get_network_by_id(network_id)
        return list(self._build_edge_json(*x) for x in g.edges_iter(data=True))

    def get_incident_edges(self, network_id, node_id):
        graph = self.get_network_by_id(network_id)
        node = self.get_node_by_id(node_id)

        successors = list(self._build_edge_json(graph, u, v, d) for u, v, d in graph.out_edges_iter(node, data=True))
        predecessors = list(self._build_edge_json(graph, u, v, d) for u, v, d in graph.in_edges_iter(node, data=True))

        return successors + predecessors

    def _query_helper(self, graph, expand_nodes=None, remove_nodes=None, **annotations):
        result = get_filtered_subgraph(
            graph,
            expand_nodes=expand_nodes,
            remove_nodes=remove_nodes,
            **annotations
        )
        add_canonical_names(result)
        self.relabel_nodes_to_identifiers(result)
        return result

    def query_all_builder(self, expand_nodes=None, remove_nodes=None, **annotations):
        return self._query_helper(self.get_super_network(), expand_nodes, remove_nodes, **annotations)

    def query_filtered_builder(self, network_id, expand_nodes=None, remove_nodes=None, **annotations):
        """Filters a dictionary from the module level cache.

        1. Thin wrapper around :code:`pybel_tools.selection.filter_graph`:
            1. Filter edges by annotations
            2. Add nodes
            3. Remove nodes
        2. Add canonical names
        3. Relabel nodes to identifiers

        :param network_id: The identifier of the network in the database
        :type network_id: int
        :param expand_nodes: Add the neighborhoods around all of these nodes
        :type expand_nodes: list
        :param remove_nodes: Remove these nodes and all of their in/out edges
        :type remove_nodes: list
        :param annotations: Annotation filters (match all with :code:`pybel.utils.subdict_matches`)
        :type annotations: dict
        :return: A BEL Graph
        :rtype: BELGraph
        """
        log.debug('Requested: %s', {
            'network_id': network_id,
            'expand': expand_nodes,
            'delete': remove_nodes,
            'annotations': annotations
        })
        graph = self.get_network_by_id(network_id)
        return self._query_helper(graph, expand_nodes, remove_nodes, **annotations)

    def get_edges(self, u, v, both_ways=True):
        """Gets the data dictionaries of all edges between the given nodes"""
        if u not in self.get_super_network():
            raise ValueError("Network doesnt have node: {}".format(u))

        if v not in self.full_network:
            raise ValueError("Network doesnt have node: {}".format(v))

        if v not in self.full_network.edge[u]:
            raise ValueError('No edges between {} and {}'.format(u, v))

        result = list(self.full_network.edge[u][v].values())

        if both_ways and v in self.full_network.edge and u in self.full_network.edge[v]:
            result.extend(self.full_network.edge[v][u].values())

        return result

    def get_nodes_containing_keyword(self, keyword):
        """Gets a list with all cnames that contain a certain keyword adding to the duplicates their function"""

        super_network = self.get_super_network()

        node_list = [data[CNAME] for n, data in super_network.nodes_iter(data=True)]

        # Case insensitive comparison
        nodes_with_keyword = [cname for cname in node_list if keyword.lower() in cname.lower()]

        duplicates_cnames = set(x for x, count in Counter(nodes_with_keyword).items() if count > 1)

        if not duplicates_cnames:
            return set(nodes_with_keyword)

        unique_cnames = set(x for x, count in Counter(nodes_with_keyword).items() if count == 1)

        duplicates_with_function = {'{}({})'.format(data[CNAME], data[FUNCTION]) for n, data in
                                    super_network.nodes_iter(data=True) if data[CNAME] in duplicates_cnames}

        nodes_with_keyword = unique_cnames.union(duplicates_with_function)

        return nodes_with_keyword

    def get_pubmed_containing_keyword(self, keyword):
        """Gets a list with pubmed_ids that contain a certain keyword"""

        super_network = self.get_super_network()

        pubmed_id_with_keyword = [pubmed_id for pubmed_id in get_pmids(super_network) if pubmed_id.startswith(keyword)]

        return pubmed_id_with_keyword

    def get_authors_containing_keyword(self, keyword):
        """Gets a list with authors that contain a certain keyword"""

        super_network = self.get_super_network()

        # Case insensitive comparison
        authors_with_keyword = [author for author in get_authors(super_network) if keyword.lower() in author.lower()]

        return authors_with_keyword
