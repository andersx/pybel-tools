# -*- coding: utf-8 -*-

"""Utilities for loading and exporting BEL graphs"""

import logging
import os

from sqlalchemy.exc import IntegrityError

from pybel import from_path, BELGraph, to_pickle, from_pickle
from pybel.io.line_utils import build_metadata_parser
from pybel.manager.cache import build_manager
from .mutation.merge import left_merge
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

    :param paths: An iterable over paths to BEL scripts
    :param paths: iter
    :param connection: A custom database connection string
    :type connection: str
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

    :param directory: A path to a directory
    :type directory: str
    :param connection: A custom database connection string
    :type connection: str
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


def convert_recursive(directory, connection=None, upload=False, pickle=False):
    metadata_parser = build_metadata_parser(connection)
    paths = list(get_paths_recursive(directory))
    log.info('Paths to parse: %s', paths)

    for path in paths:
        try:
            graph = from_path(path, manager=metadata_parser.manager)
        except Exception as e:
            log.exception('Problem parsing %s', path)

        if upload:
            try:
                metadata_parser.manager.insert_graph(graph)
            except IntegrityError as e:
                log.exception('Integrity problem')
                metadata_parser.manager.rollback()
            except Exception as e:
                log.exception('Problem uploading %s', graph.name)

        if pickle:
            new_path = '{}.gpickle'.format(path[:-4])
            to_pickle(graph, new_path)

def upload_recusive(directory, connection=None):
    manager = build_manager(connection)
    paths = list(get_paths_recursive(directory, extension='.gpickle'))
    log.info('Paths to parse: %s', paths)

    for path in paths:
        graph = from_pickle(path)

        try:
            manager.insert_graph(graph)
        except IntegrityError as e:
            log.exception('Integrity problem')
            manager.rollback()
        except Exception as e:
            log.exception('Problem uploading %s', graph.name)



def subgraphs_to_pickles(graph, directory=None, annotation='Subgraph'):
    """Groups the given graph into subgraphs by the given annotation with :func:`get_subgraph_by_annotation` and
    outputs them as gpickle files to the given directory with :func:`pybel.to_pickle`

    :param graph: A BEL Graph
    :type graph: pybel.BELGraph
    :param directory: A directory to output the pickles
    :type directory: str
    :param annotation: An annotation to split by. Suggestion: ``Subgraph``
    :type annotation: str
    """
    directory = os.getcwd() if directory is None else directory
    for value in get_annotation_values(graph, annotation=annotation):
        sg = get_subgraph_by_annotation_value(graph, annotation, value)
        sg.document.update(graph.document)

        file_name = '{}_{}.gpickle'.format(annotation, value.replace(' ', '_'))
        path = os.path.join(directory, file_name)
        to_pickle(sg, path)
