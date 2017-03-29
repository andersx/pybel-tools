# -*- coding: utf-8 -*-

"""This module serializes BEL statments to a functional JSON for use with OpenBEL API tools"""

__all__ = [
    'convert_for_belief',
]


def convert_for_belief(tokens):
    """This function takes in the tokens returned by :func:`pybel.parser.parse_bel.BelParser.parseString and modifies 
    their format to match the function/arguments format used by the OpenBEL API and BELIEF tools
    """
    raise NotImplementedError
