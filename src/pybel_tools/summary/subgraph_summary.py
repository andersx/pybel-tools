# -*- coding: utf-8 -*-

"""This module contains functions that handle and summarize subgraphs of graphs"""

from __future__ import print_function

import itertools as itt
from collections import defaultdict
from operator import itemgetter

import pandas as pd

from pybel.constants import *
from ..selection.group_nodes import group_nodes_by_annotation_filtered
from ..utils import calculate_tanimoto_set_distances, check_has_annotation, count_dict_values

__all__ = [
    'calculate_subgraph_edge_overlap',
    'summarize_subgraph_edge_overlap',
    'rank_subgraph_by_node_filter',
    'summarize_subgraph_node_overlap',
]


def calculate_subgraph_edge_overlap(graph, annotation='Subgraph'):
    """Builds a dataframe to show the overlap between different subgraphs

    Options:
    1. Total number of edges overlap (intersection)
    2. Percentage overlap (tanimoto similarity)


    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param annotation: The annotation to group by and compare. Defaults to 'Subgraph'
    :type annotation: str
    :return: {subgraph: set of edges}, {(subgraph 1, subgraph2): set of intersecting edges},
            {(subgraph 1, subgraph2): set of unioned edges}, {(subgraph 1, subgraph2): tanimoto similarity},
    """

    sg2edge = defaultdict(set)

    for u, v, d in graph.edges_iter(data=True):
        if not check_has_annotation(d, annotation):
            continue
        sg2edge[d[ANNOTATIONS][annotation]].add((u, v))

    subgraph_intersection = {}
    subgraph_union = {}
    subgraph_overlap = {}

    for sg1, sg2 in itt.combinations(sorted(sg2edge), 2):
        subgraph_intersection[sg1, sg2] = sg2edge[sg1] & sg2edge[sg2]
        subgraph_union[sg1, sg2] = sg2edge[sg1] | sg2edge[sg2]
        subgraph_overlap[sg1, sg2] = len(subgraph_intersection[sg1, sg2]) / len(subgraph_union[sg1, sg2])

    return sg2edge, subgraph_intersection, subgraph_union, subgraph_overlap


def summarize_subgraph_edge_overlap(graph, annotation='Subgraph'):
    """Returns a distance matrix between all subgraphs (or other given annotation)

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param annotation: The annotation to group by and compare. Defaults to :code:`"Subgraph"`
    :type annotation: str
    :return: A similarity matrix in a pandas dataframe
    :rtype: pd.DataFrame
    """
    sg2edge, subgraph_intersection, subgraph_union, subgraph_overlap = calculate_subgraph_edge_overlap(graph,
                                                                                                       annotation)
    labels = sorted(sg2edge)
    mat = []
    for sg1 in labels:
        row = []
        for sg2 in labels:
            if sg1 == sg2:
                row.append(1)
            elif (sg1, sg2) in subgraph_overlap:
                row.append(subgraph_overlap[sg1, sg2])
            elif (sg2, sg1) in subgraph_overlap:
                row.append(subgraph_overlap[sg2, sg1])
        mat.append(row)
    return pd.DataFrame(mat, index=labels, columns=labels)


def rank_subgraph_by_node_filter(graph, node_filter, annotation='Subgraph', reverse=True):
    """Ranks subgraphs by which have the most nodes matching an given filter

    :param graph:
    :param node_filter:
    :param annotation:
    :param reverse:
    :return:

    A use case for this function would be to identify which subgraphs contain the most differentially expressed
    genes.

    >>> from pybel import from_pickle
    >>> from pybel.constants import *
    >>> from pybel_tools.integration import overlay_type_data
    >>> from pybel_tools.summary import rank_subgraph_by_node_filter
    >>> import pandas as pd
    >>> graph = from_pickle('~/dev/bms/aetionomy/alzheimers.gpickle')
    >>> df = pd.read_csv('~/dev/bananas/data/alzheimers_dgxp.csv', columns=['Gene', 'log2fc'])
    >>> data = {gene: log2fc for _, gene, log2fc in df.itertuples()}
    >>> overlay_type_data(graph, data, 'log2fc', GENE, 'HGNC', impute=0)
    >>> results = rank_subgraph_by_node_filter(graph, lambda g, n: 1.3 < abs(g.node[n]['log2fc']))
    """

    r1 = group_nodes_by_annotation_filtered(graph, node_filter=node_filter, annotation=annotation)
    r2 = count_dict_values(r1)
    return sorted(r2.items(), key=itemgetter(1), reverse=reverse)


def summarize_subgraph_node_overlap(graph, node_filter=None, annotation='Subgraph'):
    """Calculates the subgraph similarity tanimoto similarity in nodes passing the given filter

    Provides an alternate view on subgraph similarity, from a more node-centric view

    """
    r1 = group_nodes_by_annotation_filtered(graph, node_filter=node_filter, annotation=annotation)
    r2 = calculate_tanimoto_set_distances(r1)
    return r2
