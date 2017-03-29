# -*- coding: utf-8 -*-

"""This module tests the serialization for BELIEF"""

import unittest

from pybel.constants import *
from pybel_tools.serialization.functional import convert_for_belief


@unittest.skip('Implementation not yet started')
class TestFunctionalize(unittest.TestCase):
    """These examples are taken from pybel's test functions in tests/test_parse_bel.py"""

    def test_1(self):
        tokens = {
            SUBJECT: {
                MODIFIER: ACTIVITY,
                TARGET: {
                    FUNCTION: PROTEIN,
                    IDENTIFIER: {NAMESPACE: 'HGNC', NAME: 'HMGCR'}
                },
                EFFECT: {
                    NAME: 'cat',
                    NAMESPACE: BEL_DEFAULT_NAMESPACE
                },
            },
            RELATION: 'rateLimitingStepOf',
            OBJECT: {
                FUNCTION: BIOPROCESS,
                IDENTIFIER: {NAMESPACE: 'GOBP', NAME: 'cholesterol biosynthetic process'}
            }
        }

        expected = {}

        self.assertEqual(expected, convert_for_belief(tokens))
