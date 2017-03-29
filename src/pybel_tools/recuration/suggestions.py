# -*- coding: utf-8 -*-

"""This module contains functions for making namespace suggestions"""

import requests
from requests.compat import quote_plus

__all__ = [
    'get_user_ols_search_url',
    'get_ols_suggestion',
    'get_ols_search',
]

OLS_USER_SEARCH_FMT = 'http://www.ebi.ac.uk/ols/search?q={}'
OLS_MACHINE_SUGGESTION_FMT = 'http://www.ebi.ac.uk/ols/api/suggest?q={}'
OLS_MACHINE_SEARCH_FMT = 'http://www.ebi.ac.uk/ols/api/search?q={}'


def get_user_ols_search_url(name):
    """Gets the URL of the page a user should check when they're not sure about an entity's name"""
    return OLS_USER_SEARCH_FMT.format(quote_plus(name))


def get_ols_suggestion_url(name):
    return OLS_MACHINE_SUGGESTION_FMT.format(quote_plus(name))


def get_ols_suggestion(name):
    """Gets suggestions from the Ontology Lookup Service for which name is best"""
    res = requests.get(get_ols_suggestion_url(quote_plus(name)))
    return res.json()


def get_ols_search_url(name):
    return OLS_MACHINE_SEARCH_FMT.format(name)


def get_ols_search(name):
    """Performs a search with the Ontology Lookup Service"""
    res = requests.get(get_ols_search_url(quote_plus(name)))
    return res.json()
