# -*- coding: utf-8 -*-

"""
Module that contains the command line app

Why does this file exist, and why not put this in __main__?
You might be tempted to import things from __main__ later, but that will cause
problems--the code will get executed twice:
 - When you run `python3 -m pybel_tools` python will execute
   ``__main__.py`` as a script. That means there won't be any
   ``pybel_tools.__main__`` in ``sys.modules``.
 - When you import __main__ it will get executed again (as a module) because
   there's no ``pybel_tools.__main__`` in ``sys.modules``.
Also see (1) from http://click.pocoo.org/5/setuptools/#setuptools-integration
"""

import logging
import os
import sys
from getpass import getuser

import click

import pybel.utils
from pybel import from_pickle, to_database, from_lines
from pybel.constants import DEFAULT_CACHE_LOCATION
from .definition_utils import write_namespace, export_namespaces
from .document_utils import write_boilerplate
from .ioutils import convert_recursive, upload_recusive
from .service.database_service import build_database_service_app
from .service.database_service import get_app as get_database_service_app
from .service.dict_service import build_dictionary_service_app
from .service.dict_service import get_app as get_dict_service_app
from .service.pickle_upload_service import build_pickle_uploader_app
from .utils import get_version
from .web.constants import SECRET_KEY, PYBEL_CACHE_CONNECTION
from .web.parser_endpoint import build_parser_service_app
from .web.utils import load_managers

log = logging.getLogger(__name__)


def set_debug(level):
    logging.basicConfig(level=level)
    logging.getLogger('pybel').setLevel(level)
    logging.getLogger('pybel_tools').setLevel(level)
    log.setLevel(level)


@click.group(help="PyBEL-Tools Command Line Utilities on {}".format(sys.executable))
@click.version_option()
def main():
    pass


@main.group()
def work():
    """Upload and conversion utilities"""


@work.command()
@click.argument('path')
@click.option('-c', '--connection', help='Input cache location. Defaults to {}'.format(DEFAULT_CACHE_LOCATION))
@click.option('-r', '--recursive')
@click.option('-s', '--skip-check-version', is_flag=True, help='Skip checking the PyBEL version of the gpickle')
@click.option('-v', '--debug', count=True)
def upload(path, connection, recursive, skip_check_version, debug):
    """Quick uploader"""
    if debug == 1:
        set_debug(20)
    elif debug == 2:
        set_debug(10)

    if not recursive:
        graph = from_pickle(path, check_version=(not skip_check_version))
        to_database(graph, connection=connection)
    else:
        upload_recusive(path, connection=connection)


@work.command()
@click.option('-c', '--connection', help='Input cache location. Defaults to {}'.format(DEFAULT_CACHE_LOCATION))
@click.option('-u', '--upload', is_flag=True)
@click.option('-d', '--directory', default=os.getcwd())
@click.option('-v', '--debug', count=True)
def convert(connection, upload, directory, debug):
    """Recursively converts BEL scripts to gpickles. Optional uploader"""
    if debug == 1:
        set_debug(20)
    elif debug == 2:
        set_debug(10)
    convert_recursive(directory, connection=connection, upload=upload, pickle=True)


@main.command()
@click.option('-c', '--connection', help='Cache connection string. Defaults to {}'.format(DEFAULT_CACHE_LOCATION))
@click.option('--host', help='Flask host. Defaults to localhost')
@click.option('--port', help='Flask port. Defaults to 5000')
@click.option('-v', '--debug', count=True)
@click.option('--flask-debug', is_flag=True)
@click.option('--skip-check-version', is_flag=True, help='Skip checking the PyBEL version of the gpickle')
@click.option('--run-database-service', is_flag=True, help='Use the database service')
@click.option('--run-parser-service', is_flag=True, help='Enable the single statement parser')
@click.option('--run-uploader-service', is_flag=True)
@click.option('--secret-key')
def service(connection, host, port, debug, flask_debug, skip_check_version, run_database_service, run_parser_service,
            run_uploader_service, secret_key):
    """Runs the PyBEL web service"""
    if debug == 1:
        set_debug(20)
    elif debug == 2:
        set_debug(10)

    log.info('Running PyBEL v%s', pybel.utils.get_version())
    log.info('Running PyBEL Tools v%s', get_version())

    if run_database_service:
        app = get_database_service_app()
        app.config[PYBEL_CACHE_CONNECTION] = connection
        load_managers(app)
        build_database_service_app(app)
    else:
        app = get_dict_service_app()
        app.config[PYBEL_CACHE_CONNECTION] = connection
        load_managers(app)
        build_dictionary_service_app(app, check_version=(not skip_check_version))

    if run_parser_service:
        build_parser_service_app(app)

    if run_uploader_service:
        app.config[SECRET_KEY] = secret_key if secret_key else 'pybel_default_dev_key'
        build_pickle_uploader_app(app)

    app.run(debug=flask_debug, host=host, port=port)


@main.group()
def definition():
    """Definition file utilities"""


@definition.command()
@click.argument('name')
@click.argument('keyword')
@click.argument('domain')
@click.argument('citation')
@click.option('--author', default=getuser())
@click.option('--description')
@click.option('--species')
@click.option('--version')
@click.option('--contact')
@click.option('--license')
@click.option('--values', default=sys.stdin, help="A file containing the list of names")
@click.option('--functions')
@click.option('--output', type=click.File('w'), default=sys.stdout)
@click.option('--value-prefix', default='')
def namespace(name, keyword, domain, citation, author, description, species, version, contact, license, values,
              functions, output, value_prefix):
    """Builds a namespace from items"""
    write_namespace(
        name, keyword, domain, author, citation, values,
        namespace_description=description,
        namespace_species=species,
        namespace_version=version,
        author_contact=contact,
        author_copyright=license,
        functions=functions,
        file=output,
        value_prefix=value_prefix
    )


@main.group()
def document():
    """BEL document utilities"""


@document.command()
@click.argument('document-name')
@click.argument('contact')
@click.argument('description')
@click.argument('pmids', nargs=-1)
@click.option('--version')
@click.option('--copyright')
@click.option('--authors')
@click.option('--licenses')
@click.option('--output', type=click.File('wb'), default=sys.stdout)
def boilerplate(document_name, contact, description, pmids, version, copyright, authors, licenses, output):
    """Builds a template BEL document with the given PMID's"""
    write_boilerplate(
        document_name,
        contact,
        description,
        version,
        copyright,
        authors,
        licenses,
        pmids=pmids,
        file=output
    )


@document.command()
@click.argument('namespaces', nargs=-1)
@click.option('-p', '--path', type=click.File('r'), default=sys.stdin, help='Input BEL file path. Defaults to stdin.')
@click.option('-d', '--directory', help='Output directory. Defaults to current working directory')
def serialize_namespaces(namespaces, path, directory):
    """Parses a BEL document then serializes the given namespaces (errors and all) to the given directory"""
    graph = from_lines(path)
    export_namespaces(namespaces, graph, directory)


if __name__ == '__main__':
    main()
