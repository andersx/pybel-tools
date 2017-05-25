# -*- coding: utf-8 -*-

"""This module serializes BEL statements to a functional JSON for use with OpenBEL API tools"""

from pybel.constants import *
from pybel.parser import BelParser

__all__ = [
    'convert_for_belief',
]

rev_labels = {
    ABUNDANCE: 'abundance',
    GENE: 'geneAbundance',
    MIRNA: 'microRNAAbundance',
    PROTEIN: 'proteinAbundance',
    RNA: 'rnaAbundance',
    BIOPROCESS: 'biologicalProcess',
    PATHOLOGY: 'pathology',
    COMPLEX: 'complexAbundance',
    COMPOSITE: 'compositeAbundance',

    'pep': 'peptidaseActivity',
    'cat': 'catalyticActivity',
    ACTIVITY: 'activity'
}


def parameter(namespace, name):
    return {
        'parameter': {
            'ns': namespace,
            'value': name
        }
    }


def term(func, *arguments):
    return {
        'term': {
            'fx': rev_labels.get(func, func),
            'arguments': list(arguments)
        }
    }


def parse_to_belief(statement, parser):
    """

    :param str statement: 
    :param BelParser parser: 
    :return: 
    """
    tokens = parser.parseString(statement)
    return arrange_for_belief(statement, tokens)


def arrange_for_belief(statement, tokens):
    return {
        'expression_components': convert_for_belief(tokens),
        'statement_short_form': statement
    }


def convert_for_belief(tokens):
    """This function takes in the tokens returned by :func:`pybel.parser.parse_bel.BelParser.parseString and modifies 
    their format to match the function/arguments format used by the OpenBEL API and BELIEF tools
    """
    return {
        'subject': convert_node(tokens[SUBJECT]),
        'relationship': tokens[RELATION],
        'object': convert_node(tokens[OBJECT])
    }


def _ensure_reaction(tokens):
    reactant_arguments = []
    product_arguments = []

    for reactant_tokens in tokens[REACTANTS]:
        reactant_arguments.append(convert_node(reactant_tokens))

    for product_tokens in tokens[PRODUCTS]:
        product_arguments.append(convert_node(product_tokens))

    return term(
        REACTION,
        term(REACTANTS, *reactant_arguments),
        term(PRODUCTS, *product_arguments)
    )


def _ensure_members(tokens):
    token_arguments = []
    for token in tokens[MEMBERS]:
        token_arguments.append(convert_node(token))

    return term(tokens[FUNCTION], *token_arguments)


def _ensure_variants(tokens):
    raise NotImplementedError


def _ensure_fusion(tokens):
    raise NotImplementedError


def convert_simple(tokens, location=None):
    arguments = [
        parameter(tokens[IDENTIFIER][NAMESPACE], tokens[IDENTIFIER][NAME])
    ]

    if location is not None:
        raise NotImplementedError

    return term(tokens[FUNCTION], *arguments)


def convert_node(tokens):
    if MODIFIER in tokens and tokens[MODIFIER] == DEGRADATION:
        return term(DEGRADATION, convert_node(tokens[TARGET]))

    elif MODIFIER in tokens and tokens[MODIFIER] == ACTIVITY:
        arguments = [
            convert_simple(tokens[TARGET], location=tokens.get(LOCATION))
        ]

        if TARGET in tokens:
            arguments.append(term(
                'molecularActivity',
                parameter(tokens[EFFECT][NAMESPACE], tokens[EFFECT][NAME])
            ))

        return term(ACTIVITY, *arguments)

    elif MODIFIER in tokens and tokens[MODIFIER] == TRANSLOCATION:
        return term(
            TRANSLOCATION,
            parameter(tokens[EFFECT][NAMESPACE], tokens[EFFECT][NAME]),
            term(TO_LOC, parameter(tokens[EFFECT][TO_LOC][NAMESPACE], tokens[EFFECT][TO_LOC][NAME])),
            term(FROM_LOC, parameter(tokens[EFFECT][FROM_LOC][NAMESPACE], tokens[EFFECT][FROM_LOC][NAME]))
        )

    if REACTION == tokens[FUNCTION]:
        return _ensure_reaction(tokens)

    elif MEMBERS in tokens:
        return _ensure_members(tokens)

    elif VARIANTS in tokens:
        return _ensure_variants(tokens)

    elif FUSION in tokens:
        return _ensure_fusion(tokens)

    return convert_simple(tokens)
