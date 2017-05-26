# -*- coding: utf-8 -*-

"""This module contains functions for making namespace suggestions"""

import logging

import requests
from requests.compat import quote_plus

__all__ = [
    'get_user_ols_search_url',
    'get_ols_suggestion',
    'get_ols_search',
    'help_suggest_name',
]

log = logging.getLogger(__name__)

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


def help_suggest_name(namespace, name, metadata_parser, suggestion_cache):
    """Helps populate a suggestion cache for missing names

    :param namespace: The namespace to search
    :type namespace: str
    :param name: The putative name in the namespace
    :type name: str
    :param metadata_parser: A metadata parser, which contains the namespace dictionary
    :type metadata_parser: pybel.parser.parse_metadata.MetadataParser
    :param suggestion_cache: A defaultdict of lists
    :type suggestion_cache: dict or defaultdict
    :return: 
    """
    from fuzzywuzzy import process, fuzz

    if (namespace, name) in suggestion_cache:
        return suggestion_cache[namespace, name]

    if namespace not in metadata_parser.namespace_dict:
        raise ValueError('Namespace not cached: {}'.format(namespace))

    terms = set(metadata_parser.namespace_dict[namespace])

    for putative, _ in process.extract(name, terms, scorer=fuzz.partial_token_sort_ratio, limit=5):
        suggestion_cache[namespace, name].append(putative)

    return suggestion_cache[namespace, name]


if __name__ == '__main__':
    from pybel.utils import get_bel_resource
    import os
    import json

    ptsd_ns_path = os.path.join(os.environ['OWNCLOUD_BASE'], 'namespaces', 'ptsd.belns')
    ns = get_bel_resource(ptsd_ns_path)

    c = 0
    for name in ns['Values']:
        r = get_ols_search(name)

        print(name)
        if r['response']['numFound'] == 0:
            continue
        print(json.dumps(r['response']['docs'], indent=2))
        c += 1
        if c > 20:
            break
