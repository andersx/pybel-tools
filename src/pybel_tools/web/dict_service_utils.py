# -*- coding: utf-8 -*-

"""
This module contains all of the services necessary through the PyBEL API Definition, backed by a network dictionary
"""

import logging
import time
from collections import Counter

import networkx as nx

from pybel import from_bytes, BELGraph
from pybel.canonicalize import decanonicalize_node
from pybel.manager.models import Network
from .base_service import BaseService
from ..constants import CNAME
from ..mutation.inference import infer_central_dogma
from ..mutation.merge import left_merge
from ..mutation.metadata import parse_authors, add_canonical_names
from ..selection.induce_subgraph import get_subgraph
from ..summary.edge_summary import count_comorbidities
from ..summary.provenance import get_authors, get_pmid_by_keyword, get_authors_by_keyword, get_pmids

log = logging.getLogger(__name__)


class DictionaryService(BaseService):
    """The dictionary service contains functions that implement the PyBEL API with a in-memory backend using 
    dictionaries.
    """

    def __init__(self, manager):
        """
        :param manager: A cache manager
        :type manager: pybel.manager.cache.CacheManager
        """
        BaseService.__init__(self, manager)

        #: dictionary of {int id: BELGraph graph}
        self.networks = {}

        #: dictionary of {tuple node: int id}
        self.node_nid = {}

        #: dictionary of {int id: tuple node}
        self.nid_node = {}

        #: dictionary of {str BEL: int id}
        self.bel_id = {}
        self.id_bel = {}

        #: The complete graph of all knowledge stored in the cache
        self.universe = BELGraph(**{'PYBEL_RELABELED': True})

        self.universe_pmids = set()
        self.universe_authors = set()

        #: A dictionary from {int id: {tuple node: float centrality}}
        self.node_centralities = {}

        #: A dictionary from {int id: {tuple node: int degree}}
        self.node_degrees = {}

        log.info('initialized dictionary service')

    def update_node_indexes(self, graph):
        """Updates identifiers for nodes based on addition order

        :param graph: A BEL Graph
        :type graph: pybel.BELGraph
        """
        for node in graph.nodes_iter():
            if isinstance(node, int):
                log.warning('nodes already converted to ids')
                return

            if node in self.node_nid:
                continue

            nid = len(self.node_nid)

            self.node_nid[node] = nid
            self.nid_node[nid] = node

            bel = decanonicalize_node(graph, node)
            self.id_bel[nid] = bel
            self.bel_id[bel] = nid

    def relabel_nodes_to_identifiers(self, graph):
        """Relabels all nodes by their identifiers, in place. This function is a thin wrapper around
        :func:`networkx.relabel.relabel_nodes` with the module level variable :data:`node_nid` used as the mapping.

        :param graph: A BEL Graph
        :type graph: pybel.BELGraph
        """
        if 'PYBEL_RELABELED' in graph.graph:
            log.warning('%s has already been relabeled', graph.name)
            return

        mapping = {node: self.node_nid[node] for node in graph.nodes_iter()}
        nx.relabel.relabel_nodes(graph, mapping, copy=False)

        graph.graph['PYBEL_RELABELED'] = True

    def relabel_nodes_to_pybel(self, graph):
        """Relabels all nodes to their original BEL identifiers, in place. This function is a thin wrapper around
        :func:`networkx.relabel.relabel_nodes` with the module level variable :data:`nid_node` used as the mapping. It
        is the inverse function to :meth:`relabel_nodes_to_identifiers`
        
        :param pybel.BELGraph graph: A BEL Graph
        """
        if 'PYBEL_RELABELED' not in graph.graph:
            log.warning('%s has not been relabeled to identifiers', graph.name)
            return

        mapping = {nid: self.nid_node[nid] for nid in graph.nodes_iter()}
        nx.relabel.relabel_nodes(graph, mapping, copy=False)

        del graph.graph['PYBEL_RELABELED']

    def add_network(self, graph_id, graph, force_reload=False):
        """Adds a network to the module-level cache from the underlying database

        :param int graph_id: The identifier for the graph
        :param pybel.BELGraph graph: A BEL Graph
        :param bool force_reload: Should the graphs be reloaded even if it has already been cached?
        """
        if graph_id in self.networks and not force_reload:
            log.info('tried re-adding graph [%s] %s', graph_id, graph.name)
            return

        log.info('loading network [%s] %s', graph_id, graph.name)

        log.debug('parsing authors')
        parse_authors(graph)

        log.debug('adding central dogma')
        infer_central_dogma(graph)

        log.debug('adding canonical names')
        add_canonical_names(graph)

        log.debug('updating node indexes')
        self.update_node_indexes(graph)

        log.debug('relabeling nodes by index')
        self.relabel_nodes_to_identifiers(graph)

        log.debug('adding to the universe')
        left_merge(self.universe, graph)

        log.debug('caching provenance')
        self.universe_authors |= get_authors(graph)
        self.universe_pmids |= get_pmids(graph)

        log.debug('calculating betweenness centralities (be patient)')
        t = time.time()
        self.node_centralities[graph_id] = Counter(nx.betweenness_centrality(graph))
        log.debug('done with betweenness centrality in %.2f seconds', time.time() - t)

        log.debug('calculating node degrees')
        self.node_degrees[graph_id] = Counter(graph.degree())

        self.networks[graph_id] = graph

        log.info('loaded network')

    def load_networks(self, check_version=True, force_reload=False):
        """This function needs to get all networks from the graph cache manager and make a dictionary

        :param check_version: Should the version of the BELGraphs be checked from the database? Defaults to :code`True`.
        :type check_version: bool
        :param force_reload: Should all graphs be reloaded even if they have already been cached?
        :type force_reload: bool
        """
        query = self.manager.session.query(Network.id, Network.blob)

        for network_id, network_blob in query.filter(Network.id not in self.networks).all():
            try:
                log.debug('getting bytes from [%s]', network_id)
                graph = from_bytes(network_blob, check_version=check_version)
            except:
                log.exception("couldn't load from bytes [%s]", network_id)
                continue

            self.add_network(network_id, graph, force_reload=force_reload)

    # Graph selection functions

    def get_network(self, network_id=None):
        """Gets a network by its ID or super network if identifier is not specified

        :param network_id: The internal ID of the network to get
        :type network_id: int
        :return: A BEL Graph
        :rtype: pybel.BELGraph
        """
        if network_id is None:
            log.debug('got universe (%s nodes/%s edges)', self.universe.number_of_nodes(),
                      self.universe.number_of_edges())
            return self.universe

        if network_id not in self.networks:
            network_blob = self.manager.session.query(Network.blob).get(network_id)
            log.debug('getting bytes from [%s]', network_id)
            self.add_network(network_id, from_bytes(network_blob))

        result = self.networks[network_id]
        log.debug('got network [%s] (%s nodes/%s edges)', network_id, result.number_of_nodes(),
                  result.number_of_edges())
        return result

    def decode_node(self, node_id):
        """Decodes node from URL format"""
        nid = int(node_id)

        if nid not in self.nid_node:
            raise IndexError('{} not in universe'.format(node_id))

        return nid

    def get_node_by_id(self, node_id):
        """Returns the node tuple based on the node id

        :param node_id: The node's id
        :type node_id: int or str
        :return: the node tuple
        :rtype: tuple
        """
        if isinstance(node_id, str):
            return self.nid_node[int(node_id)]

        if isinstance(node_id, int):
            return self.nid_node[node_id]

        raise TypeError('{} is wrong type: {}'.format(node_id, type(node_id)))

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
        :rtype: pybel.BELGraph
        """
        graph = self.get_network(network_id)

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

        result.graph['PYBEL_RELABELED'] = True

        log.debug('query returned (%s nodes/%s edges)', result.number_of_nodes(), result.number_of_edges())

        return result

    def get_edges(self, u, v, both_ways=True):
        """Gets the data dictionaries of all edges between the given nodes"""
        if u not in self.universe:
            raise ValueError("Network store doesn't have node: {}".format(u))

        if v not in self.universe:
            raise ValueError("Network store doesn't have node: {}".format(v))

        if v not in self.universe.edge[u]:
            raise ValueError('No edges between {} and {}'.format(u, v))

        result = list(self.universe.edge[u][v].values())

        if both_ways and v in self.universe.edge and u in self.universe.edge[v]:
            result.extend(self.universe.edge[v][u].values())

        return result

    def get_nodes_containing_keyword(self, keyword):
        """Gets a list with all cnames that contain a certain keyword adding to the duplicates their function"""
        return [{"text": bel, "id": str(nid)} for bel, nid in self.bel_id.items() if keyword.lower() in bel.lower()]

    def get_pubmed_containing_keyword(self, keyword):
        """Gets a list with pubmed_ids that contain a certain keyword
        
        :rtype: list[str]
        """
        return list(get_pmid_by_keyword(keyword, pmids=self.universe_pmids))

    def get_authors_containing_keyword(self, keyword):
        """Gets a list with authors that contain a certain keyword
        
        :rtype: list[str]
        """
        return get_authors_by_keyword(keyword, authors=self.universe_authors)

    def get_cname(self, nid):
        return self.universe.node[nid][CNAME]

    def get_top_centrality(self, graph_id, n=20):
        if graph_id not in self.node_centralities:
            self.node_centralities[graph_id] = Counter(nx.betweenness_centrality(self.get_network(graph_id)))
        return {self.get_cname(n): v for n, v in self.node_centralities[graph_id].most_common(n)}

    def get_top_degree(self, graph_id, n=20):
        if graph_id not in self.node_degrees:
            self.node_degrees[graph_id] = Counter(self.get_network(graph_id).degree())
        return {self.get_cname(n): v for n, v in self.node_degrees[graph_id].most_common(n)}

    def get_top_comorbidities(self, graph_id, n=20):
        cm = count_comorbidities(self.get_network(graph_id))
        return {self.get_cname(n): v for n, v in cm.most_common(n)}
