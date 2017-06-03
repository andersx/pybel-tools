# -*- coding: utf-8 -*-

"""Utilities for loading and exporting BEL graphs"""

import logging
import os

from sqlalchemy.exc import IntegrityError

from pybel import from_path, BELGraph, to_pickle, from_pickle
from pybel.io.line_utils import build_metadata_parser
from pybel.manager.cache import build_manager
from .integration import HGNCAnnotator
from .mutation import opening_on_central_dogma
from .mutation.merge import left_merge
from .mutation.metadata import fix_pubmed_citations
from .selection import get_subgraph_by_annotation_value
from .summary import get_annotation_values

__all__ = [
    'load_paths',
    'load_directory',
    'subgraphs_to_pickles',
]

log = logging.getLogger(__name__)


def load_paths(paths, connection=None):
    """Loads a group of BEL graphs.

    Internally, this function uses a shared :class:`pybel.parser.MetadataParser` to cache the definitions more
    efficiently.

    :param iter[str] paths: An iterable over paths to BEL scripts
    :param str connection: A custom database connection string
    :return: A BEL graph comprised of the union of all BEL graphs produced by each BEL script
    :rtype: pybel.BELGraph
    """
    metadata_parser = build_metadata_parser(connection)
    result = BELGraph()

    for path in paths:
        subgraph = from_path(path, manager=metadata_parser)
        left_merge(result, subgraph)

    return result


def load_directory(directory, connection=None):
    """Compiles all BEL scripts in the given directory and returns as a merged BEL graph using :func:`load_paths`

    :param str directory: A path to a directory
    :param str connection: A custom database connection string
    :return: A BEL graph comprised of the union of all BEL graphs produced by each BEL script
    :rtype: pybel.BELGraph
    """
    paths = (path for path in os.listdir(directory) if path.endswith('.bel'))
    return load_paths(paths, connection=connection)


def get_paths_recursive(directory, extension='.bel'):
    for root, directory, files in os.walk(directory):
        for file in files:
            if file.endswith(extension):
                yield os.path.join(root, file)


def safe_upload(manager, graph, store_parts=False):
    """Wraps uploading with try/catch so other functions can continue after"""
    try:
        manager.insert_graph(graph, store_parts=store_parts)
    except IntegrityError as e:
        log.error("Can't upload duplcate %s v%s. Consider bumping the version", graph.name, graph.version)
        manager.rollback()
    except:
        log.exception('Problem uploading %s', graph.name)


def convert_recursive(directory, connection=None, upload=False, pickle=False, store_parts=False,
                      infer_central_dogma=True, enrich_citations=False, enrich_genes=False):
    """Recursively parses and either uploads/pickles graphs in a given directory and sub-directories"""
    metadata_parser = build_metadata_parser(connection)
    hgnc_annotator = HGNCAnnotator(preload_map=enrich_genes)

    paths = list(get_paths_recursive(directory))
    log.info('Paths to parse: %s', paths)

    for path in paths:
        try:
            graph = from_path(path, manager=metadata_parser.manager)
        except:
            log.exception('Problem parsing %s', path)
            continue

        if infer_central_dogma:
            opening_on_central_dogma(graph)

        if enrich_citations:
            fix_pubmed_citations(graph)

        if enrich_genes:
            hgnc_annotator.annotate(graph)

        if upload:
            safe_upload(metadata_parser.manager, graph, store_parts=store_parts)

        if pickle:
            new_path = '{}.gpickle'.format(path[:-4])  # [:-4] gets rid of .bel at the end of the file name
            to_pickle(graph, new_path)


def upload_recursive(directory, connection=None, store_parts=False):
    """Recursively uploads all gpickles in a given directory and sub-directories
    
    :param str directory: the directory to traverse
    :param connection: A connection string or manager
    :type connection: None or str or pybel.manage.CacheManager
    :param bool store_parts: Should the edge store be used?
    """
    manager = build_manager(connection)
    paths = list(get_paths_recursive(directory, extension='.gpickle'))
    log.info('Paths to upload: %s', paths)

    for path in paths:
        graph = from_pickle(path)
        safe_upload(manager, graph, store_parts=store_parts)


def subgraphs_to_pickles(graph, directory=None, annotation='Subgraph'):
    """Groups the given graph into subgraphs by the given annotation with :func:`get_subgraph_by_annotation` and
    outputs them as gpickle files to the given directory with :func:`pybel.to_pickle`

    :param pybel.BELGraph graph: A BEL Graph
    :param str directory: A directory to output the pickles
    :param str annotation: An annotation to split by. Suggestion: ``Subgraph``
    """
    directory = os.getcwd() if directory is None else directory
    for value in get_annotation_values(graph, annotation=annotation):
        sg = get_subgraph_by_annotation_value(graph, annotation, value)
        sg.document.update(graph.document)

        file_name = '{}_{}.gpickle'.format(annotation, value.replace(' ', '_'))
        path = os.path.join(directory, file_name)
        to_pickle(sg, path)
