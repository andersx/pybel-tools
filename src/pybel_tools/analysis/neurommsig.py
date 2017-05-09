# -*- coding: utf-8 -*-

"""

The following algorithms are taken from the NeuroMMSigDB, published by Daniel Domingo Fernandez

"""

import itertools as itt
from collections import Counter

import networkx as nx

from pybel.constants import GENE
from ..filters.node_selection import get_nodes_by_function
from ..mutation.inference import infer_central_dogma


def calc_betweenness_centality(graph):
    try:
        res = Counter(nx.betweenness_centrality(graph, k=200))
        return res
    except:
        return Counter(nx.betweenness_centrality(graph))


def neurommsig_gene_ora(graph, target_genes):
    """Calculates the percentage of target genes mappable to the graph
    
    Assume: graph central dogma inferred, collapsed to genes, collapsed variants 
    
    :param pybel.BELGraph graph: A BEL graph
    :param iter[tuple] target_genes: A list of nodes
    :return: 
    :rtype: float
    """
    infer_central_dogma(graph)
    graph_genes = set(get_nodes_by_function(graph, GENE))
    return len(target_genes & graph_genes) / len(graph_genes)


def neurommsig_hubs(graph, target_genes, top=0.05):
    """Calculates the percentage of target genes mappable to the graph
    
    Assume: graph central dogma inferred, collapsed to genes, collapsed variants, graph has more than 20 nodes
    
    :param pybel.BELGraph graph: A BEL graph
    :param iter[tuple] target_genes: A list of nodes
    :rtype: float
    """
    if graph.number_of_nodes() < 20:
        raise ValueError('Graph has less than 20 nodes')

    graph_genes = set(get_nodes_by_function(graph, GENE))

    bc = Counter({k: v for k, v in calc_betweenness_centality(graph).items() if k in graph_genes})
    # TODO consider continuous analog with weighting by percentile
    n = int(0.5 + len(graph_genes) * top)

    return sum(node in target_genes for node in bc.most_common(n)) / n


def neurommsig_topology(graph, nodes):
    """Calculates the node neighbor score for a given list of nodes.
    
    -  Doesn't consider self loops
    
    :param pybel.BELGraph graph: A BEL graph
    :param iter[tuple] nodes: A list of nodes
    :rtype: float
    
    .. math::
        
         \frac{\sum_i^n N_G[i]}{n*(n-1)}
    
    :param pybel.BELGraph graph: A BEL graph
    :param iter[tuple] nodes: A list of nodes
    :rtype: float
    """
    nodes = list(nodes)
    n = len(nodes)
    return sum(u in graph.edge[v] for u, v in itt.product(nodes, repeat=2) if u != v) / (n * (n - 1))


def weighted_neurommsig_score(graph, target_genes, ora_weight=1, hub_weight=1, topology_weight=1):
    """Calculates the composite NeuroMMSig Score for a given list of genes
    
    :param pybel.BELGraph graph: A BEL graph
    :param iter[tuple] nodes: A list of gene nodes 
    :param ora_weight: 
    :param hub_weight: 
    :param topology_weight: 
    :return: The NeuroMMSig composite score
    :rtype: float
    """
    ora_score = neurommsig_gene_ora(graph, target_genes)
    hub_score = neurommsig_hubs(graph, target_genes)
    topology_score = neurommsig_topology(graph, target_genes)

    weighted_sum = ora_weight * ora_score + hub_weight * hub_score + topology_weight * topology_score
    total_weight = ora_weight + hub_weight + topology_weight
    return weighted_sum / total_weight
