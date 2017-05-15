import unittest

from pybel import BELGraph
from pybel.constants import *
from pybel_tools.selection.group_nodes import get_mapped


class TestMapping(unittest.TestCase):
    def test_my_shit(self):
        g = BELGraph()

        g.add_node('APP', attr_dict={NAMESPACE: 'HGNC', NAME: 'APP'})
        g.add_node('APP Fragment')
        g.add_edge('APP', 'APP Fragment', **{RELATION: HAS_VARIANT})

        mapped_nodes = get_mapped(g, 'HGNC', {'APP'})

        self.assertEqual(1, len(mapped_nodes))
        self.assertIn('APP', mapped_nodes)
        self.assertEqual({'APP Fragment'}, mapped_nodes['APP'])
