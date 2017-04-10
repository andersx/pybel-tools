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
from ..selection import get_subgraph
from ..summary import get_authors, get_pmids
from ..utils import citation_to_tuple

log = logging.getLogger(__name__)


def _node_to_identifier(node, graph):
    return hash_tuple(graph.nodes[node])


class DictionaryService(BaseService):
    """The dictionary service contains functions that implement the PyBEL API with a in-memory backend using 
    dictionaries.
    """

    def __init__(self, manager):
        """
        :param manager: The database connection string. Default location described in
                           :class:`pybel.manager.cache.BaseCacheManager`
        
        :type manager: pybel.manager.cache.CacheManager
        """
        BaseService.__init__(self, manager)

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
            log.info('tried adding network [%s] again')
            return

        parse_authors(graph)
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
        :func:`networkx.relabel.relabel_nodes` with the module level variable :code:`node_id` used as the mapping.

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

    def get_network_by_id(self, network_id=None):
        """Gets a network by its ID or super network if identifier is not specified

        :param network_id: The internal ID of the network to get
        :type network_id: int
        :return: A BEL Graph
        :rtype: BELGraph
        """
        result = self.networks[network_id] if network_id is not None else self.get_super_network()
        log.debug('got network %s (%s nodes/%s edges)', network_id, result.number_of_nodes(), result.number_of_edges())
        return result

    def load_super_network(self):
        """Reloads the super network"""
        for graph in self.networks.values():
            left_merge(self.full_network, graph)

        parse_authors(self.full_network)

        log.info(
            'loaded super network. %s nodes and %s edges',
            self.full_network.number_of_nodes(),
            self.full_network.number_of_edges()
        )

        self.full_network_loaded = True

    def get_super_network(self, reload=False):
        """Gets all networks and merges them together. Caches in self.full_network.

        :return: A BEL Graph
        :rtype: pybel.BELGraph
        """
        if not reload and self.full_network_loaded:
            return self.full_network

        self.load_super_network()

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

    def get_incident_edges(self, network_id, node_id):
        graph = self.get_network_by_id(network_id)
        node = self.get_node_by_id(node_id)

        successors = list(self._build_edge_json(graph, u, v, d) for u, v, d in graph.out_edges_iter(node, data=True))
        predecessors = list(self._build_edge_json(graph, u, v, d) for u, v, d in graph.in_edges_iter(node, data=True))

        return successors + predecessors

    def query(self, network_id=None, seed_method=None, seed_data=None, expand_nodes=None, remove_nodes=None,
              **annotations):
        """Filters a dictionary from the module level cache.
        
        0. Gets network by ID or uses merged network store
        1. Thin wrapper around :func:`pybel_tools.selection.get_subgraph`:
            1. Apply seed function
            2. Filter edges by annotations
            3. Add nodes
            4. Remove nodes
        2. Add canonical names
        3. Relabel nodes to identifiers

        :param network_id: The identifier of the network in the database. If none, gets all networks merged with
                            :func:`get_super_network`
        :type network_id: int
        :param seed_method: The name of the get_subgraph_by_* function to use
        :type seed_method: str or None
        :param seed_data: The argument to pass to the :func:`pybel_tools.selection.get_subgraph`
        :param expand_nodes: Add the neighborhoods around all of these nodes
        :type expand_nodes: list
        :param remove_nodes: Remove these nodes and all of their in/out edges
        :type remove_nodes: list
        :param annotations: Annotation filters (match all with :func:`pybel.utils.subdict_matches`)
        :type annotations: dict
        :return: A BEL Graph
        :rtype: BELGraph
        """
        graph = self.get_network_by_id(network_id)

        log.debug('query: %s', {
            'seed_method': seed_method,
            'seed_data': seed_data,
            'expand': expand_nodes,
            'delete': remove_nodes,
            'annotations': annotations
        })

        result = get_subgraph(
            graph,
            seed_method=seed_method,
            seed_data=seed_data,
            expand_nodes=expand_nodes,
            remove_nodes=remove_nodes,
            **annotations
        )

        log.debug('query returned (%s nodes/%s edges)', result.number_of_nodes(), result.number_of_edges())

        add_canonical_names(result)
        self.relabel_nodes_to_identifiers(result)

        return result

    def get_edges(self, u, v, both_ways=True):
        """Gets the data dictionaries of all edges between the given nodes"""
        graph = self.get_super_network()

        if u not in graph:
            raise ValueError("Network doesnt have node: {}".format(u))

        if v not in graph:
            raise ValueError("Network doesnt have node: {}".format(v))

        if v not in graph.edge[u]:
            raise ValueError('No edges between {} and {}'.format(u, v))

        result = list(graph.edge[u][v].values())

        if both_ways and v in graph.edge and u in graph.edge[v]:
            result.extend(graph.edge[v][u].values())

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

    def list_namespaces(self):
        return sorted(self.manager.list_namespaces())

    def list_annotations(self):
        return sorted(self.manager.list_annotations())
