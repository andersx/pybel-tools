"""
This module contains all of the services necessary through the PyBEL API Definition, backed by a network
dictionary
"""

import json
import logging
from collections import OrderedDict, defaultdict

import networkx as nx

from pybel import from_bytes, BELGraph
from pybel.constants import *
from pybel.io import to_json_dict
from pybel.manager.graph_cache import GraphCacheManager
from pybel.manager.models import Network
from ..mutation import add_canonical_names
from ..selection import filter_graph

log = logging.getLogger(__name__)

#: dictionary of {int id: BELGraph graph}
networks = {}

#: dictionary of {tuple node: int id}
node_id = {}

#: dictionary of {int id: tuple node}
id_node = {}


# Helper functions

def _validate_network_id(network_id):
    if network_id not in networks:
        raise ValueError()


def _citation_to_tuple(citation):
    return tuple([
        citation.get(CITATION_TYPE),
        citation.get(CITATION_NAME),
        citation.get(CITATION_REFERENCE),
        citation.get(CITATION_DATE),
        citation.get(CITATION_AUTHORS),
        citation.get(CITATION_COMMENTS)
    ])


def _build_edge_json(u, v, d):
    return {
        'source': u,
        'target': v,
        'data': d
    }


def _node_to_identifier(node, graph):
    return hash(graph.nodes[node])


# Graph loading functions

def load_networks(connection=None, check_version=True):
    """This function needs to get all networks from the graph cache manager and make a dictionary"""
    gcm = GraphCacheManager(connection=connection)

    for nid, blob in gcm.session.query(Network.id, Network.blob).all():
        log.info('loading network %s')
        graph = from_bytes(blob, check_version=check_version)
        networks[nid] = graph

    update_node_indexes()


# Graph mutation functions

def update_node_indexes():
    for network_id in get_network_ids():
        network = get_network_by_id(network_id)
        update_node_indexes_by_graph(network)


def update_node_indexes_by_graph(graph):
    """Updates identifiers for nodes based on addition order

    :param graph: A BEL Graph
    :type graph: BELGraph
    """
    for node in graph.nodes_iter():
        if node in node_id:
            continue

        node_id[node] = len(node_id)
        id_node[node_id[node]] = node


def relabel_nodes_to_hashes(graph):
    """Relabels all nodes by their hashes, in place

    :param graph: A BEL Graph
    :type graph: BELGraph
    """
    nx.relabel.relabel_nodes(graph, node_id, copy=False)


# Graph selection functions

def get_network_ids():
    """Returns a list of all network IDs

    :rtype: list of int
    """
    return list(networks)


def get_network_by_id(network_id):
    """Gets a network by its ID

    :param network_id: The internal ID of the network to get
    :type network_id: int
    :return: A BEL Graph
    :rtype: BELGraph
    """
    return networks[network_id]


def get_namespaces_in_network(network_id):
    return list(get_network_by_id(network_id).namespace_url.values())


def get_annotations_in_network(network_id):
    return list(get_network_by_id(network_id).annotation_url.values())


def get_citations_in_network(network_id):
    g = get_network_by_id(network_id)
    citations = set(data[CITATION] for _, _, data in g.edges_iter(data=True))
    return list(sorted(citations, key=_citation_to_tuple))


def get_edges_in_network(network_id):
    g = get_network_by_id(network_id)
    return list(_build_edge_json(*x) for x in g.edges_iter(data=True))


def get_edges_in_network_filtered(network_id, **kwargs):
    g = get_network_by_id(network_id)
    return list(_build_edge_json(u, v, d) for u, v, d in g.edges_iter(data=True, **kwargs))


def query_builder(network_id, expand_nodes=None, remove_nodes=None, **kwargs):
    """

    1. Match by annotations
    2. Add nodes
    3. Remove nodes

    :param network_id: The identifier of the network in the database
    :type network_id: int
    :param expand_nodes: Add the neighborhoods around all of these nodes
    :type expand_nodes: list
    :param remove_nodes: Remove these nodes and all of their in/out edges
    :type remove_nodes: list
    :param kwargs: Annotation filters (match all with :code:`pybel.utils.subdict_matches`)
    :type kwargs: dict
    :return: A BEL Graph
    :rtype: BELGraph
    """
    original_graph = get_network_by_id(network_id)
    result_graph = filter_graph(original_graph, expand_nodes=expand_nodes, remove_nodes=remove_nodes, **kwargs)

    add_canonical_names(result_graph)
    relabel_nodes_to_hashes(result_graph)

    return result_graph


def to_node_link(graph):
    """Converts the graph to a JSON object that is appropriate for the PyBEL API. This is not necessarily the same
    as :code:`pybel.io.to_json_dict` because that function makes a standard node-link structure, and this function
    auguments/improves on the standard structure.

    :param graph: A BEL Graph
    :type graph: BELGraph
    :return: The JSON object representing this dictionary
    :rtype: dict
    """
    json_graph = to_json_dict(graph)
    return json.dumps(OrderedDict([("nodes", json_graph['nodes']), ("links", json_graph['links'])]), ensure_ascii=False)


# Graph set all filters

# TODO @ddomingof create view for rendering the filters only in multiple dropdowns wrapped in a form
# @ddomingof see pybel_utils.summary.get_unique_annotations
def graph_dict_filter(graph):
    """ Creates a dictionary with annotation type as keys and set of annotations as values"""

    graph_dict = defaultdict(set)
    for _, _, data in graph.edges_iter(data=True):
        for key, value in data['annotations'].items():
            graph_dict[key].add(value)

    return graph_dict