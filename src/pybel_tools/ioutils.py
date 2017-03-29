# -*- coding: utf-8 -*-

"""Utilities for loading and exporting BEL graphs"""

import os

from pybel import from_path, BELGraph
from pybel.manager.cache import CacheManager
from pybel.parser import MetadataParser
from .mutation.merge import left_merge

__all__ = [
    'load_paths',
    'load_directory',
]


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
    cm = CacheManager(connection=connection)
    mp = MetadataParser(cache_manager=cm)
    result_graph = BELGraph()

    for path in paths:
        subgraph = from_path(path, manager=mp)
        left_merge(result_graph, subgraph)

    return result_graph


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
