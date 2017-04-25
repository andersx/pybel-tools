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

import pybel
from pybel import from_pickle, to_database, from_lines
from pybel.constants import SMALL_CORPUS_URL, LARGE_CORPUS_URL, get_cache_connection
from pybel.manager.cache import build_manager
from pybel.utils import get_version as pybel_version
from .constants import GENE_FAMILIES, NAMED_COMPLEXES
from .definition_utils import write_namespace, export_namespaces
from .document_utils import write_boilerplate
from .ioutils import convert_recursive, upload_recursive
from .mutation.metadata import fix_pubmed_citations
from .utils import get_version
from .web import receiver_service
from .web.analysis_service import build_analysis_service
from .web.compilation_service import build_synchronous_compiler_service
from .web.constants import SECRET_KEY
from .web.database_service import build_database_service
from .web.dict_service import build_dictionary_service
from .web.parser_endpoint import build_parser_service
from .web.receiver_service import build_receiver_service, DEFAULT_SERVICE_URL
from .web.sitemap_endpoint import build_sitemap_endpoint
from .web.upload_service import build_pickle_uploader_service
from .web.utils import get_app

log = logging.getLogger(__name__)

datefmt = '%H:%M:%S'
fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def set_debug(level):
    logging.basicConfig(level=level, format=fmt, datefmt=datefmt)
    pybel_log = logging.getLogger('pybel')
    pybel_log.setLevel(level)
    pbt_log = logging.getLogger('pybel_tools')
    pbt_log.setLevel(level)
    log.setLevel(level)


def set_debug_param(debug):
    if debug == 1:
        set_debug(20)
    elif debug == 2:
        set_debug(10)


@click.group(help="PyBEL-Tools Command Line Utilities on {}\n with PyBEL v{}".format(sys.executable, pybel_version()))
@click.version_option()
def main():
    pass


@main.group()
def ensure():
    """Utilities for ensuring data"""


@ensure.command()
@click.option('-c', '--connection', help='Cache connection. Defaults to {}'.format(get_cache_connection()))
@click.option('--enrich-authors', is_flag=True)
@click.option('--use-edge-store', is_flag=True)
@click.option('-v', '--debug', count=True, help="Turn on debugging. More v's, more debugging")
def small_corpus(connection, enrich_authors, use_edge_store, debug):
    """Caches the Selventa Small Corpus"""
    set_debug_param(debug)
    manager = build_manager(connection)
    graph = pybel.from_url(SMALL_CORPUS_URL, manager=manager, citation_clearing=False, allow_nested=True)
    if enrich_authors:
        fix_pubmed_citations(graph)
    manager.insert_graph(graph, store_parts=use_edge_store)


@ensure.command()
@click.option('-c', '--connection', help='Cache connection. Defaults to {}'.format(get_cache_connection()))
@click.option('--enrich-authors', is_flag=True)
@click.option('--use-edge-store', is_flag=True)
@click.option('-v', '--debug', count=True, help="Turn on debugging. More v's, more debugging")
def large_corpus(connection, enrich_authors, use_edge_store, debug):
    """Caches the Selventa Large Corpus"""
    set_debug_param(debug)
    manager = build_manager(connection)
    graph = pybel.from_url(LARGE_CORPUS_URL, manager=manager, citation_clearing=False, allow_nested=True)
    if enrich_authors:
        fix_pubmed_citations(graph)
    manager.insert_graph(graph, store_parts=use_edge_store)


@ensure.command()
@click.option('-c', '--connection', help='Cache connection. Defaults to {}'.format(get_cache_connection()))
@click.option('--enrich-authors', is_flag=True)
@click.option('--use-edge-store', is_flag=True)
@click.option('-v', '--debug', count=True, help="Turn on debugging. More v's, more debugging")
def gene_families(connection, enrich_authors, use_edge_store, debug):
    """Caches the HGNC Gene Family memberships"""
    set_debug_param(debug)
    manager = build_manager(connection)
    graph = pybel.from_url(GENE_FAMILIES, manager=manager)
    if enrich_authors:
        fix_pubmed_citations(graph)
    manager.insert_graph(graph, store_parts=use_edge_store)


@ensure.command()
@click.option('-c', '--connection', help='Cache connection. Defaults to {}'.format(get_cache_connection()))
@click.option('--enrich-authors', is_flag=True)
@click.option('--use-edge-store', is_flag=True)
@click.option('-v', '--debug', count=True, help="Turn on debugging. More v's, more debugging")
def named_complexes(connection, enrich_authors, use_edge_store, debug):
    """Caches GO Named Protein Complexes memberships"""
    set_debug_param(debug)
    manager = build_manager(connection)
    graph = pybel.from_url(NAMED_COMPLEXES, manager=manager)
    if enrich_authors:
        fix_pubmed_citations(graph)
    manager.insert_graph(graph, store_parts=use_edge_store)


@main.group()
def io():
    """Upload and conversion utilities"""


@io.command()
@click.option('-p', '--path', default=os.getcwd())
@click.option('-c', '--connection', help='Cache connection. Defaults to {}'.format(get_cache_connection()))
@click.option('-r', '--recursive', is_flag=True,
              help='Recursively upload all gpickles in the directory given as the path')
@click.option('-s', '--skip-check-version', is_flag=True, help='Skip checking the PyBEL version of the gpickle')
@click.option('--to-service', is_flag=True, help='Sends to PyBEL web service')
@click.option('--service-url', help='Service location. Defaults to {}'.format(DEFAULT_SERVICE_URL))
@click.option('-v', '--debug', count=True, help="Turn on debugging. More v's, more debugging")
def upload(path, connection, recursive, skip_check_version, to_service, service_url, debug):
    """Quick uploader"""
    set_debug_param(debug)
    if recursive:
        log.info('uploading recursively from: %s', path)
        upload_recursive(path, connection=connection)
    else:
        graph = from_pickle(path, check_version=(not skip_check_version))
        if to_service:
            receiver_service.post(graph, service_url)
        else:
            to_database(graph, connection=connection)


@io.command()
@click.argument('path')
@click.option('-u', '--url', help='Service location. Defaults to {}'.format(DEFAULT_SERVICE_URL))
@click.option('-s', '--skip-check-version', is_flag=True, help='Skip checking the PyBEL version of the gpickle')
def post(path, url, skip_check_version):
    """Posts the given graph to the PyBEL Web Service via JSON"""
    graph = from_pickle(path, check_version=(not skip_check_version))
    receiver_service.post(graph, url)


@io.command()
@click.option('-c', '--connection', help='Cache connection. Defaults to {}'.format(get_cache_connection()))
@click.option('-u', '--upload', is_flag=True, help='Enable automatic database uploading')
@click.option('--store-parts', is_flag=True, help='Automatically upload to database and edge store')
@click.option('-d', '--directory', default=os.getcwd(),
              help='The directory to search. Defaults to current working directory')
@click.option('-v', '--debug', count=True, help="Turn on debugging. More v's, more debugging")
def convert(connection, upload, store_parts, directory, debug):
    """Recursively walks the file tree and converts BEL scripts to gpickles. Optional uploader"""
    set_debug_param(debug)
    convert_recursive(directory, connection=connection, upload=(upload or store_parts), pickle=True,
                      store_parts=store_parts)


@main.command()
@click.option('-c', '--connection', help='Cache connection. Defaults to {}'.format(get_cache_connection()))
@click.option('--host', help='Flask host. Defaults to localhost')
@click.option('--port', type=int, help='Flask port. Defaults to 5000')
@click.option('-v', '--debug', count=True, help="Turn on debugging. More v's, more debugging")
@click.option('--flask-debug', is_flag=True, help="Turn on werkzeug debug mode")
@click.option('--skip-check-version', is_flag=True, help='Skip checking the PyBEL version of the gpickle')
@click.option('-e', '--eager', is_flag=True, help="Eagerly preload all data and perform enrichments")
@click.option('--run-database-service', is_flag=True, help='Enable the database service')
@click.option('--run-parser-service', is_flag=True, help='Enable the single statement parser service')
@click.option('--run-receiver-service', is_flag=True, help='Enable the JSON receiver service')
@click.option('--run-analysis-service', is_flag=True, help='Enable the analysis service')
@click.option('-a', '--run-all', is_flag=True, help="Enable *all* services")
@click.option('--secret-key', help='Set the CSRF secret key')
@click.option('--admin-password', help='Set admin password and enable admin services')
@click.option('--echo-sql', is_flag=True)
def web(connection, host, port, debug, flask_debug, skip_check_version, eager, run_database_service, run_parser_service,
        run_receiver_service, run_analysis_service, run_all, secret_key,
        admin_password, echo_sql):
    """Runs PyBEL Web"""
    set_debug_param(debug)

    log.info('Running PyBEL v%s', pybel_version())
    log.info('Running PyBEL Tools v%s', get_version())

    if host is not None:
        log.info('Running on host: %s', host)

    if port is not None:
        log.info('Running on port: %d', port)

    app = get_app()
    app.config[SECRET_KEY] = secret_key if secret_key else 'pybel_default_dev_key'

    manager = build_manager(connection, echo=echo_sql)

    admin_password = admin_password or (('PYBEL_ADMIN_PASS' in os.environ) and os.environ['PYBEL_ADMIN_PASS'])

    build_sitemap_endpoint(app, show_admin=admin_password)

    api = build_dictionary_service(
        app,
        manager=manager,
        check_version=(not skip_check_version),
        admin_password=admin_password,
        analysis_enabled=(run_analysis_service or run_all),
        eager=eager,
    )

    build_synchronous_compiler_service(app, manager=manager)
    build_pickle_uploader_service(app, manager=manager)

    if run_database_service:
        build_database_service(app, manager)

    if run_parser_service or run_all:
        build_parser_service(app)

    if run_receiver_service or run_all:
        build_receiver_service(app, manager=manager)

    if run_analysis_service or run_all:
        build_analysis_service(app, manager=manager, api=api)

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
