# -*- coding: utf-8 -*-

"""Utilities for serializing to BEL namespace and BEL annotation files"""

from __future__ import print_function

import getpass
import logging
import os
import sys
import time

from pybel.constants import NAMESPACE_DOMAIN_TYPES, belns_encodings, METADATA_AUTHORS, METADATA_CONTACT, METADATA_NAME
from pybel.manager.utils import parse_owl
from pybel.utils import get_bel_resource
from .summary.error_summary import get_incorrect_names
from .summary.node_summary import get_names

__all__ = [
    'make_namespace_header',
    'make_author_header',
    'make_citation_header',
    'make_properties_header',
    'write_namespace',
    'write_namespace_from_owl',
    'make_annotation_header',
    'write_annotation',
    'export_namespace',
    'export_namespaces',
    'get_merged_namespace_names',
]

log = logging.getLogger(__name__)

DATETIME_FMT = '%Y-%m-%dT%H:%M:%S'
DATE_FMT = '%Y-%m-%d'


def make_namespace_header(name, keyword, domain, query_url=None, description=None, species=None, version=None,
                          created=None):
    """Makes the ``[Namespace]`` section of a BELNS file

    :param name: The namespace name
    :param keyword: Preferred BEL Keyword, maximum length of 8
    :param domain: One of: :code:`BiologicalProcess`, :code:`Chemical`, :code:`Gene and Gene Products`,
                   or :code:`Other`
    :param query_url: HTTP URL to query for details on namespace values (must be valid URL)
    :param description: Namespace description
    :param species: Comma-separated list of species taxonomy id's
    :param version: Namespace version. Defaults to :code:`1.0.0`
    :param created: Namespace public timestamp, ISO 8601 datetime
    :type created: str
    :return: An iterator over the lines of the ``[Namespace]`` section of a BELNS file
    :rtype: iter
    """
    if domain not in NAMESPACE_DOMAIN_TYPES:
        raise ValueError('Invalid domain: {}. Should be one of: {}'.format(domain, NAMESPACE_DOMAIN_TYPES))

    yield '[Namespace]'
    yield 'Keyword={}'.format(keyword)
    yield 'NameString={}'.format(name)
    yield 'DomainString={}'.format(domain)
    yield 'VersionString={}'.format(version if version else '1.0.0')
    yield 'CreatedDateTime={}'.format(created if created else time.strftime(DATETIME_FMT))

    if description is not None:
        yield 'DescriptionString={}'.format(description)

    if species is not None:
        yield 'SpeciesString={}'.format(species)

    if query_url is not None:
        yield 'QueryValueURL={}'.format(query_url)


def make_author_header(name=None, contact=None, copyright_str=None):
    """Makes the ``[Author]`` section of a BELNS file

    :param name: Namespace's authors
    :param contact: Namespace author's contact info/email address
    :param copyright_str: Namespace's copyright/license information. Defaults to :code:`Other/Proprietary`
    :return: An iterable over the ``[Author]`` section of a BELNS file
    :rtype: iter
    """
    yield '[Author]'
    yield 'NameString={}'.format(name if name is not None else getpass.getuser())
    yield 'CopyrightString={}'.format('Other/Proprietary' if copyright_str is None else copyright_str)

    if contact is not None:
        yield 'ContactInfoString={}'.format(contact)


def make_citation_header(name, description=None, url=None, version=None, date=None):
    """Makes the ``[Citation]`` section of a BEL config file.

    :param name: Citation name
    :type name: str
    :param description: Citation description
    :param url: URL to more citation information
    :param version: Citation version
    :param date: Citation publish timestamp, ISO 8601 Date
    :return: An iterable over the lines of the ``[Citation]`` section of a BEL config file
    :rtype: iter
    """
    yield '[Citation]'
    yield 'NameString={}'.format(name)

    if date is not None:
        yield 'PublishedDate={}'.format(date)

    if version is not None:
        yield 'PublishedVersionString={}'.format(version)

    if description is not None:
        yield 'DescriptionString={}'.format(description)

    if url is not None:
        yield 'ReferenceURL={}'.format(url)


def make_properties_header(case_sensitive=True, delimiter='|', cacheable=True):
    """Makes the ``[Processing]`` section of a BEL config file.
    
    :param case_sensitive: Should this config file be interpreted as case-sensitive?
    :type case_sensitive: bool
    :param delimiter: The delimiter between names and labels in this config file
    :type delimiter: str
    :param cacheable: Should this config file be cached?
    :type cacheable: bool
    :return: An iterable over the lines in the ``[Processing]`` section of a BEL config file
    :rtype: iter
    """
    yield '[Processing]'
    yield 'CaseSensitiveFlag={}'.format('yes' if case_sensitive else 'no')
    yield 'DelimiterString={}'.format(delimiter)
    yield 'CacheableFlag={}'.format('yes' if cacheable else 'no')


def write_namespace(namespace_name, namespace_keyword, namespace_domain, author_name, citation_name, values,
                    namespace_description=None, namespace_species=None, namespace_version=None,
                    namespace_query_url=None, namespace_created=None, author_contact=None, author_copyright=None,
                    citation_description=None, citation_url=None, citation_version=None, citation_date=None,
                    case_sensitive=True, delimiter='|', cacheable=True, functions=None, file=None, value_prefix='',
                    sort_key=None):
    """Writes a BEL namespace (BELNS) to a file

    :param namespace_name: The namespace name
    :type namespace_name: str
    :param namespace_keyword: Preferred BEL Keyword, maximum length of 8
    :type namespace_keyword: str
    :param namespace_domain: One of: :code:`BiologicalProcess`, :code:`Chemical`, :code:`Gene and Gene Products`,
                             or :code:`Other`
    :type namespace_domain: str
    :param author_name: The namespace's authors
    :type author_name: str
    :param citation_name: The name of the citation
    :type citation_name: str
    :param values: An iterable of values (strings)
    :type values: iter
    :param namespace_query_url: HTTP URL to query for details on namespace values (must be valid URL)
    :type namespace_query_url: str
    :param namespace_description: Namespace description
    :type namespace_description: str
    :param namespace_species: Comma-separated list of species taxonomy id's
    :type namespace_species: str
    :param namespace_version: Namespace version
    :type namespace_version: str
    :param namespace_created: Namespace public timestamp, ISO 8601 datetime
    :type namespace_created: str
    :param author_contact: Namespace author's contact info/email address
    :type author_contact: str
    :param author_copyright: Namespace's copyright/license information
    :type author_copyright: str
    :param citation_description: Citation description
    :type citation_description: str
    :param citation_url: URL to more citation information
    :type citation_url: str
    :param citation_version: Citation version
    :type citation_version: str
    :param citation_date: Citation publish timestamp, ISO 8601 Date
    :type citation_date: str
    :param case_sensitive: Should this config file be interpreted as case-sensitive?
    :type case_sensitive: bool
    :param delimiter: The delimiter between names and labels in this config file
    :type delimiter: str
    :param cacheable: Should this config file be cached?
    :type cacheable: bool
    :param functions: The encoding for the elements in this namespace
    :type functions: iterable of characters
    :param file: the stream to print to
    :type file: file or file-like
    :param value_prefix: a prefix for each name
    :type value_prefix: str
    :param sort_key: A function to sort the values with :code:`sorted`
    """
    file = sys.stdout if file is None else file

    for line in make_namespace_header(namespace_name, namespace_keyword, namespace_domain,
                                      query_url=namespace_query_url, description=namespace_description,
                                      species=namespace_species, version=namespace_version, created=namespace_created):
        print(line, file=file)
    print(file=file)

    for line in make_author_header(author_name, contact=author_contact, copyright_str=author_copyright):
        print(line, file=file)
    print(file=file)

    for line in make_citation_header(citation_name, description=citation_description, url=citation_url,
                                     version=citation_version, date=citation_date):
        print(line, file=file)
    print(file=file)

    for line in make_properties_header(case_sensitive=case_sensitive, delimiter=delimiter, cacheable=cacheable):
        print(line, file=file)
    print(file=file)

    function_values = ''.join(sorted(functions if functions is not None else belns_encodings.keys()))

    print('[Values]', file=file)

    values = sorted(values) if sort_key is None else sorted(values, key=sort_key)
    for value in values:
        if not value.strip():
            continue
        print('{}{}|{}'.format(value_prefix, value.strip(), function_values), file=file)


def write_namespace_from_owl(url, file=None):
    """

    :param url: Path to OWL file or filelike object
    :type url: str
    :param file: output stream. Defaults to :code:`sys.stdout` if None
    :type file: file or file-like
    """

    owl = parse_owl(url)

    write_namespace(owl['title'],
                    owl['subject'],
                    owl['description'],
                    'Other',
                    owl['creator'],
                    owl['email'],
                    url,
                    owl.graph.nodes(),
                    file=file)


def make_annotation_header(keyword, description=None, usage=None, version=None, created=None):
    """Makes the ``[AnnotationDefinition]`` section of a BELANNO file

    :param keyword: Preferred BEL Keyword, maximum length of 8
    :type keyword: str
    :param description: A description of this annotation
    :type description: str
    :param usage: How to use this annotation
    :type usage: str
    :param version: Namespace version. Defaults to '1.0.0'
    :type version: str
    :param created: Namespace public timestamp, ISO 8601 datetime
    :type created: str
    :return: A iterator over the lines for the ``[AnnotationDefinition]`` section
    :rtype: iter
    """

    yield '[AnnotationDefinition]'
    yield 'Keyword={}'.format(keyword)
    yield 'TypeString={}'.format('list')
    yield 'VersionString={}'.format(version if version else '1.0.0')
    yield 'CreatedDateTime={}'.format(created if created else time.strftime(DATETIME_FMT))

    if description is not None:
        yield 'DescriptionString={}'.format(description)

    if usage is not None:
        yield 'UsageString={}'.format(usage)


def write_annotation(keyword, values, citation_name, description=None, usage=None, version=None, created=None,
                     author_name=None, author_copyright=None, author_contact=None, case_sensitive=True, delimiter='|',
                     cacheable=True, file=None, value_prefix=''):
    """Writes a BEL annotation (BELANNO) to a file

    :param keyword: The annotation keyword
    :type keyword: str
    :param values: A dictionary of {name: label}
    :type values: dict
    :param citation_name: The citation name
    :type citation_name: str
    :param description: A description of this annotation
    :type description: str
    :param usage: How to use this annotation
    :type usage: str
    :param version: The version of this annotation (defaults to ``1.0.0``)
    :type version: str
    :param created: The annotation's public timestamp, ISO 8601 datetime
    :type created: str
    :param author_name: The author's name
    :type author_name: str
    :param author_copyright: The copyright information for this annotation. Defaults to ``Other/Proprietary``
    :type author_copyright: str
    :param author_contact: The contact information for the author of this annotation.
    :type author_contact: str
    :param case_sensitive: Should this config file be interpreted as case-sensitive?
    :type case_sensitive: bool
    :param delimiter: The delimiter between names and labels in this config file
    :type delimiter: str
    :param cacheable: Should this config file be cached?
    :type cacheable: bool
    :param file: A file or file-like
    :type file: file
    :param value_prefix: An optional prefix for all values
    :type value_prefix: str
    """
    file = sys.stdout if file is None else file

    for line in make_annotation_header(keyword, description=description, usage=usage, version=version, created=created):
        print(line, file=file)
    print(file=file)

    for line in make_author_header(name=author_name, contact=author_contact, copyright_str=author_copyright):
        print(line, file=file)
    print(file=file)

    print('[Citation]', file=file)
    print('NameString={}'.format(citation_name), file=file)
    print(file=file)

    for line in make_properties_header(case_sensitive=case_sensitive, delimiter=delimiter, cacheable=cacheable):
        print(line, file=file)
    print(file=file)

    print('[Values]', file=file)
    for key, value in sorted(values.items()):
        if not key.strip():
            continue
        print('{}{}|{}'.format(value_prefix, key.strip(), value.strip()), file=file)


def export_namespace(graph, namespace, directory=None, cacheable=False):
    """Exports all names and missing names from the given namespace to its own BEL Namespace files in the given
    directory.

    Could be useful during quick and dirty curation, where planned namespace building is not a priority.

    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param namespace: The namespace to process
    :type namespace: str
    :param directory: The path to the directory where to output the namespace. Defaults to the current working
                      directory returned by :func:`os.getcwd`
    :type directory: str
    :param cacheable: Should the namespace be cacheable? Defaults to ``False`` because, in general, this operation 
                        will probably be used for evil, and users won't want to reload their entire cache after each
                        iteration of curation.
    :type cacheable: bool
    """
    directory = os.getcwd() if directory is None else directory
    path = os.path.join(directory, '{}.belns'.format(namespace))

    with open(path, 'w') as file:
        right_names, wrong_names = get_names(graph, namespace), get_incorrect_names(graph, namespace)
        log.info('Outputting %d correct and %d wrong names to %s', len(right_names), len(wrong_names), path)
        names = (right_names | wrong_names)

        if 0 == len(names):
            log.warning('%s is empty', namespace)

        write_namespace(
            namespace_name=namespace,
            namespace_keyword=namespace,
            namespace_domain='Other',
            author_name=graph.document.get(METADATA_AUTHORS),
            author_contact=graph.document.get(METADATA_CONTACT),
            citation_name=graph.document.get(METADATA_NAME),
            values=names,
            cacheable=cacheable,
            file=file
        )


def export_namespaces(graph, namespaces, directory=None, cacheable=False):
    """Thinly wraps :func:`export_namespace` for an iterable of namespaces.
    
    :param graph: A BEL graph
    :type graph: pybel.BELGraph
    :param namespaces: An iterable of strings for the namespaces to process
    :type namespaces: iter
    :param directory: The path to the directory where to output the namespaces. Defaults to the current working
                      directory returned by :func:`os.getcwd`
    :type directory: str
    :param cacheable: Should the namespaces be cacheable? Defaults to ``False`` because, in general, this operation 
                        will probably be used for evil, and users won't want to reload their entire cache after each 
                        iteration of curation.
    :type cacheable: bool
    """
    directory = os.getcwd() if directory is None else directory  # avoid making multiple calls to os.getcwd later
    for namespace in namespaces:
        export_namespace(graph, namespace, directory=directory, cacheable=cacheable)


def get_merged_namespace_names(locations, check_keywords=True):
    """Loads many namespaces and combines their names.
    
    :param locations: An iterable of URLs or file paths pointing to BEL namespaces.
    :type locations: iter
    :param check_keywords: Should all the keywords be the same? Defaults to ``True``
    :type check_keywords: bool
    :return: A dictionary of {names: labels}
    :rtype: dict
    
    Example Usage
    
    >>> graph = ...
    >>> original_ns_url = ...
    >>> export_namespace(graph, 'MBS') # Outputs in current directory to MBS.belns
    >>> value_dict = get_merged_namespace_names([original_ns_url, 'MBS.belns'])
    >>> with open('merged_namespace.belns', 'w') as f:
    >>> ...  write_namespace('MyBrokenNamespace', 'MBS', 'Other', 'Charles Hoyt', 'PyBEL Citation', value_dict, file=f)
    """
    resources = {location: get_bel_resource(location) for location in locations}

    if check_keywords:
        resource_keywords = set(config['Namespace']['Keyword'] for config in resources.values())
        if 1 != len(resource_keywords):
            raise ValueError('Tried merging namespaces with different keywords: {}'.format(resource_keywords))

    result = {}
    for resource in resources:
        result.update(resource['Values'])
    return result
