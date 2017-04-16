# -*- coding: utf-8 -*-

import unittest

from pybel import BELGraph
from pybel_tools.filters import filter_nodes, keep_node_permissive


class TestNodeFilters(unittest.TestCase):
    def setUp(self):
        self.universe = BELGraph()

        self.universe.add_edge(1, 2)
        self.universe.add_edge(2, 3)
        self.universe.add_edge(3, 7)
        self.universe.add_edge(1, 4)
        self.universe.add_edge(1, 5)
        self.universe.add_edge(5, 6)
        self.universe.add_edge(8, 2)

        self.graph = BELGraph()
        self.graph.add_edge(1, 2)

    def test_keep_permissive(self):
        nodes = set(filter_nodes(self.universe, keep_node_permissive))
        self.assertEqual({1, 2, 3, 4, 5, 6, 7, 8}, nodes)
