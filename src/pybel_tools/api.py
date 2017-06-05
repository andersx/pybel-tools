# -*- coding: utf-8 -*-

"""
This module contains all of the services necessary through the PyBEL API Definition, backed by a network dictionary
"""

import logging
import time
from collections import Counter

import networkx as nx
from sqlalchemy import func

from pybel import from_bytes, BELGraph
from pybel.canonicalize import decanonicalize_node, calculate_canonical_name
from pybel.manager.models import Network
from .constants import CNAME
from .mutation.expansion import expand_internal
from .mutation.inference import infer_central_dogma
from .mutation.merge import left_merge
from .mutation.metadata import parse_authors, add_canonical_names, fix_pubmed_citations
from .selection.induce_subgraph import get_subgraph
from .summary.edge_summary import count_diseases
from .summary.provenance import get_authors, get_pmid_by_keyword, get_authors_by_keyword, get_pubmed_identifiers
from .utils import calc_betweenness_centality

log = logging.getLogger(__name__)

CENTRALITY_SAMPLES = 200


class BaseService(object):
    """The base service class provides a functional interface that all PyBEL services must implement"""

    def __init__(self, manager):
        """
        :param pybel.manager.cache.CacheManager manager: A cache manager
        """
        self.manager = manager


class DictionaryService(BaseService):
    """The dictionary service contains functions that implement the PyBEL API with a in-memory backend using 
    dictionaries.
    """

    def __init__(self, manager):
        """
        :param pybel.manager.cache.CacheManager manager: A cache manager
        """
        super(DictionaryService, self).__init__(manager)

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

    def clear(self):
        self.__init__(self.manager)

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

    def add_network(self, network_id, graph, force_reload=False, eager=False):
        """Adds a network to the module-level cache from the underlying database

        :param int network_id: The identifier for the graph
        :param pybel.BELGraph graph: A BEL Graph
        :param bool force_reload: Should the graphs be reloaded even if it has already been cached?
        :param bool eager: Should data be calculated/loaded eagerly?
        """
        if network_id in self.networks and not force_reload:
            log.info('tried re-adding graph [%s] %s', network_id, graph.name)
            return

        log.info('loading network [%s] %s v%s', network_id, graph.name, graph.version)

        log.debug('parsing authors')
        parse_authors(graph)

        log.debug('inferring central dogma')
        infer_central_dogma(graph)

        log.debug('adding canonical names')
        add_canonical_names(graph)

        log.debug('updating node indexes')
        self.update_node_indexes(graph)

        log.debug('relabeling nodes by index')
        self.relabel_nodes_to_identifiers(graph)

        log.debug('calculating node degrees')
        self.node_degrees[network_id] = Counter(graph.degree())

        log.debug('caching PubMed identifiers')
        self.universe_pmids |= get_pubmed_identifiers(graph)

        if eager:
            log.debug('calculating centralities (be patient)')
            t = time.time()
            bc = calc_betweenness_centality(graph)
            self.node_centralities[network_id] = Counter(bc)
            log.debug('done with betweenness centrality in %.2f seconds', time.time() - t)

            log.debug('enriching citations')
            t = time.time()
            fix_pubmed_citations(graph)
            log.debug('done enriching citations in %.2f seconds', time.time() - t)

        log.debug('caching authors')
        self.universe_authors |= get_authors(graph)

        log.debug('adding to the universe')
        left_merge(self.universe, graph)

        self.networks[network_id] = graph

        log.info('loaded network')

    def load_networks(self, check_version=True, force_reload=False, eager=False):
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

            self.add_network(network_id, graph, force_reload=force_reload, eager=eager)

        log.info('universe has (%s nodes/%s edges)', self.universe.number_of_nodes(), self.universe.number_of_edges())

    # Graph selection functions

    def get_network(self, network_id=None):
        """Gets a network by its ID or super network if identifier is not specified

        :param int network_id: The internal ID of the network to get
        :return: A BEL Graph
        :rtype: pybel.BELGraph
        """
        if network_id is None:
            log.debug('got universe (%s nodes/%s edges)', self.universe.number_of_nodes(),
                      self.universe.number_of_edges())
            return self.universe

        if network_id not in self.networks:
            network = self.manager.session.query(Network).get(network_id)
            log.debug('getting bytes from [%s]', network_id)
            self.add_network(network_id, from_bytes(network.blob))

        result = self.networks[network_id]
        log.debug('got network [%s] (%s nodes/%s edges)', result, result.number_of_nodes(), result.number_of_edges())
        return result

    def decode_node(self, node_id):
        """Decodes node from URL format"""
        nid = int(node_id)

        if nid not in self.nid_node:
            raise IndexError('{} not in universe'.format(node_id))

        return nid

    def get_node_id(self, node):
        return self.node_nid[node]

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
              filters=None, filter_pathologies=False, **annotations):
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
        :param list filters: Filters to apply to nodes
        :param bool filter_pathologies: Should pathology nodes be removed?
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
            'annotations': annotations,
            'filter_pathologies': filter_pathologies,
        })

        if filters:
            log.debug('filtering is not implemented yet, but got: %s', filters)

        result = get_subgraph(
            graph,
            seed_method=seed_method,
            seed_data=seed_data,
            expand_nodes=expand_nodes,
            remove_nodes=remove_nodes,
            filter_pathologies=filter_pathologies,
            **annotations
        )

        # Only expand on internal edges if we've done some adding
        if seed_method or expand_nodes:
            expand_internal(graph, result)

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
        return list(get_pmid_by_keyword(keyword, pubmed_identifiers=self.universe_pmids))

    def get_authors_containing_keyword(self, keyword):
        """Gets a list with authors that contain a certain keyword
        
        :rtype: list[str]
        """
        return get_authors_by_keyword(keyword, authors=self.universe_authors)

    def get_cname(self, node):
        if CNAME in self.universe.node[node]:
            return self.universe.node[node][CNAME]

        self.universe.node[node][CNAME] = calculate_canonical_name(self.universe, node)
        return self.universe.node[node][CNAME]

    def get_top_centrality(self, network_id, count=20):
        if network_id not in self.node_centralities:
            log.info('lazy loading centralities for [%s]', network_id)
            t = time.time()
            graph = self.get_network(network_id)
            bc = calc_betweenness_centality(graph)
            self.node_centralities[network_id] = Counter(bc)
            log.info('loaded centralities in %.2f seconds', time.time() - t)
        return {self.get_cname(node): v for node, v in self.node_centralities[network_id].most_common(count)}

    def get_top_degree(self, network_id, count=20):
        if network_id not in self.node_degrees:
            log.info('lazy loading degrees for [%s]', network_id)
            graph = self.get_network(network_id)
            self.node_degrees[network_id] = Counter(graph.degree())
        return {self.get_cname(node): v for node, v in self.node_degrees[network_id].most_common(count)}

    def get_top_comorbidities(self, network_id, count=20):
        graph = self.get_network(network_id)
        cm = count_diseases(graph)
        return {self.get_cname(node): v for node, v in cm.most_common(count)}

    def list_graphs(self):
        """Lists the most recently uploaded version of each network"""
        return self.manager.session.query(Network).group_by(Network.name).having(func.max(Network.created)).order_by(
            Network.created.desc()).all()

    def list_public_graphs(self):
        """Lists the graphs that have been made public"""
        results = []

        for network in self.list_graphs():
            if not network.report:  # no report means uploaded automatically or by admin
                results.append(network)
            elif network.report[0].public:
                results.append(network)

        return results


class DatabaseService(BaseService):
    """Provides queries to access data stored in the PyBEL edge store"""

    def get_namespaces(self, network_id=None, offset_start=0, offset_end=500, name_list=False, keyword=None):
        """Provides a list of namespaces filtered by the given parameters.

        :param network_id: Primary identifier of the network in the PyBEL database. This can be obtained with the
                           get_networks function.
        :type network_id: int
        :param offset_start: The starting point of the offset (position in database)
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
            network = self.manager.get_network_by_id(network_id)
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
            network = self.manager.get_network_by_id(network_id)
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
            network = self.manager.get_network_by_id(network_id)
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
            network = self.manager.get_network_by_id(network_id)

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
            network = self.manager.get_network_by_id(network_id)
            result = [node.data for node in network.nodes[offset_start:offset_end]]
        else:
            result = self.manager.get_node(bel=bel, namespace=namespace, name=name, as_dict_list=True)

        return result
