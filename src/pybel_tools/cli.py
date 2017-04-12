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

from pybel import from_pickle, to_database, from_lines
from pybel.constants import DEFAULT_CACHE_LOCATION
from pybel.manager.cache import build_manager
from pybel.utils import get_version as pybel_version
from .definition_utils import write_namespace, export_namespaces
from .document_utils import write_boilerplate
from .ioutils import convert_recursive, upload_recusive
from .service.compilation_service import build_synchronous_compiler_service
from .service.database_service import build_database_service
from .service.database_service import get_app as get_database_service_app
from .service.dict_service import build_dictionary_service
from .service.dict_service import get_app as get_dict_service_app
from .service.receiver_service import build_receiver_service, DEFAULT_SERVICE_URL
from .service.receiver_service import post as send_to_service
from .service.summary_service import build_summary_service
from .service.upload_service import build_pickle_uploader_service
from .utils import get_version
from .web.constants import SECRET_KEY, PYBEL_CACHE_CONNECTION
from .web.parser_endpoint import build_parser_service
from .web.sitemap_endpoint import build_sitemap_endpoint

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
def io():
    """Upload and conversion utilities"""


@io.command()
@click.argument('path')
@click.option('-c', '--connection', help='Input cache location. Defaults to {}'.format(DEFAULT_CACHE_LOCATION))
@click.option('-r', '--recursive', help='Recursively upload all gpickles in the directory given as the path')
@click.option('-s', '--skip-check-version', is_flag=True, help='Skip checking the PyBEL version of the gpickle')
@click.option('--to-service', is_flag=True, help='Sends to PyBEL web service')
@click.option('-v', '--debug', count=True, help="Turn on debugging. More v's, more debugging")
def upload(path, connection, recursive, skip_check_version, to_service, debug):
    """Quick uploader"""
    if debug == 1:
        set_debug(20)
    elif debug == 2:
        set_debug(10)

    if recursive:
        upload_recusive(path, connection=connection)
    else:
        graph = from_pickle(path, check_version=(not skip_check_version))
        if to_service:
            send_to_service(graph)
        else:
            to_database(graph, connection=connection)


@io.command()
@click.argument('path')
@click.option('-u', '--url', help='Service location. Defautls to {}'.format(DEFAULT_SERVICE_URL))
@click.option('-s', '--skip-check-version', is_flag=True, help='Skip checking the PyBEL version of the gpickle')
def post(path, url, skip_check_version):
    graph = from_pickle(path, check_version=(not skip_check_version))
    send_to_service(graph, url)


@io.command()
@click.option('-c', '--connection', help='Input cache location. Defaults to {}'.format(DEFAULT_CACHE_LOCATION))
@click.option('-u', '--upload', is_flag=True, help='Enable automatic database uploading')
@click.option('-d', '--directory', default=os.getcwd(),
              help='The directory to search. Defaults to current working directory')
@click.option('-v', '--debug', count=True, help="Turn on debugging. More v's, more debugging")
def convert(connection, upload, directory, debug):
    """Recursively walks the file tree and converts BEL scripts to gpickles. Optional uploader"""
    if debug == 1:
        set_debug(20)
    elif debug == 2:
        set_debug(10)
    convert_recursive(directory, connection=connection, upload=upload, pickle=True)


@main.command()
@click.option('-c', '--connection', help='Cache connection string. Defaults to {}'.format(DEFAULT_CACHE_LOCATION))
@click.option('--host', help='Flask host. Defaults to localhost')
@click.option('--port', help='Flask port. Defaults to 5000')
@click.option('-v', '--debug', count=True, help="Turn on debugging. More v's, more debugging")
@click.option('--flask-debug', is_flag=True, help="Turn on werkzeug debug mode")
@click.option('--skip-check-version', is_flag=True, help='Skip checking the PyBEL version of the gpickle')
@click.option('--run-database-service', is_flag=True, help='Use the database service')
@click.option('--run-parser-service', is_flag=True, help='Enable the single statement parser service')
@click.option('--run-uploader-service', is_flag=True, help='Enable the gpickle upload page')
@click.option('--run-compiler-service', is_flag=True, help='Enable the compiler page')
@click.option('--run-summary-service', is_flag=True, help='Enable the graph summary page')
@click.option('--run-receiver-service', is_flag=True, help='Enable the graph receiver service')
@click.option('-a', '--run-all', is_flag=True, help="Enable *all* services")
@click.option('--secret-key', help='Set the CSRF secret key')
@click.option('--admin-password')
def web(connection, host, port, debug, flask_debug, skip_check_version, run_database_service, run_parser_service,
        run_uploader_service, run_compiler_service, run_summary_service, run_receiver_service, run_all, secret_key,
        admin_password):
    """Runs PyBEL Web"""
    if debug == 1:
        set_debug(20)
    elif debug == 2:
        set_debug(10)

    log.info('Running PyBEL v%s', pybel_version())
    log.info('Running PyBEL Tools v%s', get_version())

    manager = build_manager(connection)

    if run_database_service:
        app = get_database_service_app()
        app.config[PYBEL_CACHE_CONNECTION] = connection
        build_database_service(app, manager=manager)
    else:
        app = get_dict_service_app()
        app.config[PYBEL_CACHE_CONNECTION] = connection
        build_dictionary_service(app, manager=manager, check_version=(not skip_check_version),
                                 admin_password=admin_password)

    app.config[SECRET_KEY] = secret_key if secret_key else 'pybel_default_dev_key'

    if run_parser_service or run_all:
        build_parser_service(app)

    if run_uploader_service or run_all:
        build_pickle_uploader_service(app, manager=manager)

    if run_summary_service or run_all:
        build_summary_service(app, manager=manager)

    if run_compiler_service or run_all:
        build_synchronous_compiler_service(app, manager=manager)

    if run_receiver_service or run_all:
        build_receiver_service(app, manager=manager)

    build_sitemap_endpoint(app)

    log.info('Done building %s', app)
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
    """Builds a template BEL document with the given PubMed identifiers"""
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
