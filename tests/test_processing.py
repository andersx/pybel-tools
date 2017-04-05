# -*- coding: utf-8 -*-

import unittest

import pybel
from pybel.constants import *
from pybel_tools.mutation import remove_leaves_by_type, prune_central_dogma, infer_missing_inverse_edge, \
    infer_central_dogma


class TestProcessing(unittest.TestCase):
    def setUp(self):
        if 'PYBEL_BASE' in os.environ:
            test_bel_simple_path = os.path.join(os.environ['PYBEL_BASE'], 'tests', 'bel', 'test_bel.bel')
            self.graph = pybel.from_path(test_bel_simple_path)
        else:
            test_bel_simple_url = 'https://raw.githubusercontent.com/pybel/pybel/develop/tests/bel/test_bel.bel'
            self.graph = pybel.from_url(test_bel_simple_url)

        infer_central_dogma(self.graph)

        n1 = GENE, 'HGNC', 'AKT1'
        n2 = RNA, 'HGNC', 'EGFR'

        n3 = GENE, 'HGNC', 'DUMMY1'
        self.graph.add_node(n3, attr_dict={FUNCTION: GENE, NAMESPACE: 'HGNC', NAME: 'DUMMY1'})

        n4 = GENE, 'HGNC', 'DUMMY2'
        self.graph.add_node(n4, attr_dict={FUNCTION: RNA, NAMESPACE: 'HGNC', NAME: 'DUMMY2'})

        self.graph.add_edge(n1, n3)
        self.graph.add_edge(n2, n4)

    def test_base(self):
        self.assertEqual(14, self.graph.number_of_nodes())
        self.assertEqual(16, self.graph.number_of_edges())

    def test_prune_by_type(self):
        remove_leaves_by_type(self.graph, GENE)
        self.assertEqual(10, self.graph.number_of_nodes())

    def test_prune(self):
        prune_central_dogma(self.graph)
        self.assertEqual(9, self.graph.number_of_nodes())

    def test_infer(self):
        infer_missing_inverse_edge(self.graph, TRANSLATED_TO)
        self.assertEqual(20, self.graph.number_of_edges())
