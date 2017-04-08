# -*- coding: utf-8 -*-

"""This module contains functions that help add more data to the network"""

import logging

from pybel.constants import NAME
from . import pipeline
from .filters.node_filters import filter_nodes, function_namespace_inclusion_builder

__all__ = [
    'overlay_data',
    'overlay_type_data',
]

log = logging.getLogger(__name__)


@pipeline.in_place_mutator
def overlay_data(graph, data, label, overwrite=False):
    """Overlays tabular data on the network

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param data: A dictionary of {pybel node: data for that node}
    :type data: dict
    :param label: The annotation label to put in the node dictionary
    :type label: str
    :param overwrite: Should old annotations be overwritten?
    :type overwrite: bool
    """
    for node, annotation in data.items():
        if node not in graph:
            log.debug('%s not in graph', node)
            continue
        elif label in graph.node[node] and not overwrite:
            log.debug('%s already on %s', label, node)
            continue
        graph.node[node][label] = annotation


# TODO switch label to be kwarg with default value DATA_WEIGHT
@pipeline.in_place_mutator
def overlay_type_data(graph, data, label, function, namespace, overwrite=False, impute=None):
    """Overlays tabular data on the network for data that comes from an data set with identifiers that lack
    namespaces.

    For example, if you want to overlay differential gene expression data from a table, that table
    probably has HGNC identifiers, but no specific annotations that they are in the HGNC namespace or
    that the entities to which they refer are RNA.

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param data: A dictionary of {name: data}
    :type data: dict
    :param label: The annotation label to put in the node dictionary
    :type label: str
    :param function: The function of the keys in the data dictionary
    :type function: str
    :param namespace: The namespace of the keys in the data dictionary
    :type namespace: str
    :param overwrite: Should old annotations be overwritten?
    :type overwrite: bool
    :param impute: The value to use for missing data
    """
    new_data = {}

    for node in filter_nodes(graph, function_namespace_inclusion_builder(function, namespace)):
        new_data[node] = data.get(graph.node[node][NAME], impute)

    overlay_data(graph, new_data, label, overwrite=overwrite)
