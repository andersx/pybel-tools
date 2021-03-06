# -*- coding: utf-8 -*-

import unittest

from pybel import BELGraph
from pybel.constants import *
from pybel.constants import unqualified_edge_code
from pybel_tools.mutation import collapse_by_central_dogma, collapse_nodes
from pybel_tools.mutation.inference import infer_central_dogmatic_transcriptions, infer_central_dogmatic_translations

HGNC = 'HGNC'

g1 = GENE, HGNC, '1'
r1 = RNA, HGNC, '1'
p1 = PROTEIN, HGNC, '1'

g2 = GENE, HGNC, '2'
r2 = RNA, HGNC, '2'
p2 = PROTEIN, HGNC, '2'

g3 = GENE, HGNC, '3'
r3 = RNA, HGNC, '3'
p3 = PROTEIN, HGNC, '3'

g4 = GENE, HGNC, '4'
m4 = MIRNA, HGNC, '4'


class TestCollapseDownstream(unittest.TestCase):
    def test_collapse_1(self):
        graph = BELGraph()

        graph.add_simple_node(*p1)
        graph.add_simple_node(*p2)
        graph.add_simple_node(*p3)

        graph.add_edge(p1, p3, **{RELATION: INCREASES})
        graph.add_edge(p2, p3, **{RELATION: DIRECTLY_INCREASES})

        self.assertEqual(3, graph.number_of_nodes())
        self.assertEqual(2, graph.number_of_edges())

        d = {
            p1: {p2}
        }

        collapse_nodes(graph, d)

        self.assertEqual(2, graph.number_of_nodes())
        self.assertEqual(2, graph.number_of_edges(), msg=graph.edges(data=True, keys=True))

    def test_collapse_dogma_1(self):
        graph = BELGraph()

        graph.add_simple_node(*p1)
        graph.add_simple_node(*r1)

        graph.add_edge(r1, p1, key=unqualified_edge_code[TRANSLATED_TO], **{RELATION: TRANSLATED_TO})

        self.assertEqual(2, graph.number_of_nodes())
        self.assertEqual(1, graph.number_of_edges())

        collapse_by_central_dogma(graph)

        self.assertEqual(1, graph.number_of_nodes())
        self.assertEqual(0, graph.number_of_edges())

    def test_collapse_dogma_2(self):
        graph = BELGraph()

        graph.add_simple_node(*p1)
        graph.add_simple_node(*r1)
        graph.add_simple_node(*g1)

        graph.add_edge(r1, p1, key=unqualified_edge_code[TRANSLATED_TO], **{RELATION: TRANSLATED_TO})
        graph.add_edge(g1, r1, key=unqualified_edge_code[TRANSCRIBED_TO], **{RELATION: TRANSCRIBED_TO})

        self.assertEqual(3, graph.number_of_nodes())
        self.assertEqual(2, graph.number_of_edges())

        collapse_by_central_dogma(graph)

        self.assertEqual(1, graph.number_of_nodes())
        self.assertEqual(0, graph.number_of_edges())

    def test_collapse_dogma_3(self):
        graph = BELGraph()

        graph.add_simple_node(*r1)
        graph.add_simple_node(*g1)

        graph.add_edge(g1, r1, key=unqualified_edge_code[TRANSCRIBED_TO], **{RELATION: TRANSCRIBED_TO})

        self.assertEqual(2, graph.number_of_nodes())
        self.assertEqual(1, graph.number_of_edges())

        collapse_by_central_dogma(graph)

        self.assertEqual(1, graph.number_of_nodes())
        self.assertEqual(0, graph.number_of_edges())


class TestInference(unittest.TestCase):
    def test_infer_1(self):
        graph = BELGraph()

        graph.add_simple_node(*p1)
        graph.add_simple_node(*g1)
        graph.add_simple_node(*p2)
        graph.add_simple_node(*g3)
        graph.add_simple_node(*m4)

        graph.add_edge(p1, p2, **{RELATION: INCREASES})
        graph.add_edge(g1, g3, **{RELATION: POSITIVE_CORRELATION})

        self.assertEqual(5, graph.number_of_nodes())
        self.assertEqual(2, graph.number_of_edges())

        infer_central_dogmatic_translations(graph)

        self.assertEqual(7, graph.number_of_nodes())
        self.assertEqual(4, graph.number_of_edges())
        self.assertIn(r1, graph)
        self.assertIn(r2, graph)

        infer_central_dogmatic_transcriptions(graph)

        self.assertEqual(9, graph.number_of_nodes())
        self.assertEqual(7, graph.number_of_edges())
        self.assertIn(g1, graph)
        self.assertIn(g2, graph)
        self.assertIn(g3, graph)
        self.assertIn(g4, graph)

        collapse_by_central_dogma(graph)

        self.assertEqual(4, graph.number_of_nodes())
        self.assertEqual(2, graph.number_of_edges())

        self.assertTrue(graph.has_edge(p1, g3))
        self.assertTrue(graph.has_edge(p1, p2))
