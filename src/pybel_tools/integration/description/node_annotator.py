# -*- coding: utf-8 -*-

import abc

import six

from ...filters import get_nodes_by_namespace

__all__ = [
    'add_descriptions',
    'NodeAnnotator',
]


def add_descriptions(graph, namespace, node_annotator):
    """Adds descriptions to all nodes using a given node annotator instance.

    Assumes iteration over a namespace that has names.

    :param pybel.BELGraph graph: A BEL graph
    :param str namespace: The namespace to interrogate
    :param NodeAnnotator node_annotator: A node annotator for the given namespace
    """
    for node in get_nodes_by_namespace(graph, namespace):
        name = graph.get_node_name(node)
        description = node_annotator.get_description(name)
        graph.set_node_description(node, description)


@six.add_metaclass(abc.ABCMeta)
class NodeAnnotator(object):
    """A node annotator"""

    def __init__(self, namespace):
        """
        :param str namespace: The name of the namespace that this node annotator services
        """
        self.namespace = namespace

    @abc.abstractmethod
    def get_description(self, name):
        """Gets the description for the given name in"""

    def get_label(self, name):
        """Gets the label for the given name in. Worst case scenario, canonicalizes the node as the label"""

    def annotate(self, graph):
        for node in get_nodes_by_namespace(graph, self.namespace):
            name = graph.get_node_name(node)

            description = self.get_description(name)
            graph.set_node_description(node, description)

            label = self.get_label(name)
            graph.set_node_label(node, label if label else name)
