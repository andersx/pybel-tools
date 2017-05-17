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

from pybel import from_pickle, to_database, from_lines, from_url
from pybel.constants import PYBEL_LOG_DIR, SMALL_CORPUS_URL, LARGE_CORPUS_URL, get_cache_connection
from pybel.manager.cache import build_manager
from pybel.manager.models import Base
from pybel.utils import get_version as pybel_version
from .constants import GENE_FAMILIES, NAMED_COMPLEXES
from .definition_utils import write_namespace, export_namespaces
from .document_utils import write_boilerplate
from .ioutils import convert_recursive, upload_recursive
from .mutation.metadata import fix_pubmed_citations
from .utils import get_version, enable_cool_mode
from .web import receiver_service
from .web.analysis_service import build_analysis_service
from .web.compilation_service import build_synchronous_compiler_service
from .web.constants import reporting_log, DEFAULT_SERVICE_URL, PYBEL_WEB_PASSWORD_SALT
from .web.curation_service import build_curation_service
from .web.database_service import build_database_service
from .web.dict_service import build_dictionary_service
from .web.github_login_service import build_github_login_service, login_log
from .web.parser_endpoint import build_parser_service
from .web.receiver_service import build_receiver_service
from .web.reporting_service import build_reporting_service
from .web.security import build_security_service, User, Role, PYBEL_ADMIN_ROLL_NAME
from .web.sitemap_endpoint import build_sitemap_endpoint
from .web.upload_service import build_pickle_uploader_service
from .web.utils import get_app

log = logging.getLogger(__name__)

datefmt = '%H:%M:%S'
fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

reporting_log.setLevel(logging.DEBUG)
reporting_fh = logging.FileHandler(os.path.join(PYBEL_LOG_DIR, 'reporting.txt'))
reporting_fh.setLevel(logging.DEBUG)
reporting_fh.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
reporting_log.addHandler(reporting_fh)

login_log.setLevel(logging.DEBUG)
login_log_fh = logging.FileHandler(os.path.join(PYBEL_LOG_DIR, 'logins.txt'))
login_log_fh.setLevel(logging.DEBUG)
login_log_fh.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
login_log.addHandler(login_log_fh)


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
    graph = from_url(SMALL_CORPUS_URL, manager=manager, citation_clearing=False, allow_nested=True)
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
    graph = from_url(LARGE_CORPUS_URL, manager=manager, citation_clearing=False, allow_nested=True)
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
    graph = from_url(GENE_FAMILIES, manager=manager)
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
    graph = from_url(NAMED_COMPLEXES, manager=manager)
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
@click.option('-u', '--enable-upload', is_flag=True, help='Enable automatic database uploading')
@click.option('--store-parts', is_flag=True, help='Automatically upload to database and edge store')
@click.option('--no-enrich-authors', is_flag=True, help="Don't enrich authors. Makes faster.")
@click.option('-d', '--directory', default=os.getcwd(),
              help='The directory to search. Defaults to current working directory')
@click.option('-v', '--debug', count=True, help="Turn on debugging. More v's, more debugging")
@click.option('-x', '--cool', is_flag=True, help='enable cool mode')
def convert(connection, enable_upload, store_parts, no_enrich_authors, directory, debug, cool):
    """Recursively walks the file tree and converts BEL scripts to gpickles. Optional uploader"""
    set_debug_param(debug)

    if cool:
        enable_cool_mode()

    convert_recursive(directory, connection=connection, upload=(enable_upload or store_parts), pickle=True,
                      store_parts=store_parts, enrich_citations=(not no_enrich_authors))


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
@click.option('-a', '--run-all', is_flag=True, help="Enable *all* services")
@click.option('--secret-key', help='Set the CSRF secret key')
@click.option('--no-preload', is_flag=True, help='Do not preload cache')
@click.option('--basic-security', is_flag=True, help='use basic security instead of github')
@click.option('--echo-sql', is_flag=True)
def web(connection, host, port, debug, flask_debug, skip_check_version, eager, run_database_service, run_parser_service,
        run_receiver_service, run_all, secret_key, no_preload, basic_security, echo_sql):
    """Runs PyBEL Web"""
    set_debug_param(debug)
    if debug < 3:
        enable_cool_mode()

    log.info('Running PyBEL v%s', pybel_version())
    log.info('Running PyBEL Tools v%s', get_version())

    if host is not None:
        log.info('Running on host: %s', host)

    if port is not None:
        log.info('Running on port: %d', port)

    app = get_app()
    app.config.update({
        'SECRET_KEY': secret_key if secret_key else 'pybel_default_dev_key',
    })

    manager = build_manager(connection, echo=echo_sql)

    if basic_security:
        app.config.update({
            'SECURITY_REGISTERABLE': True,
            'SECURITY_CONFIRMABLE': False,
            'SECURITY_SEND_REGISTER_EMAIL': False,
            'SECURITY_PASSWORD_HASH': 'pbkdf2_sha512',
            'SECURITY_PASSWORD_SALT': os.environ[PYBEL_WEB_PASSWORD_SALT],
        })
        Base.metadata.bind = manager.engine
        Base.query = manager.session.query_property()
        build_security_service(app, manager)
    else:
        build_github_login_service(app)

    api = build_dictionary_service(
        app,
        manager=manager,
        check_version=(not skip_check_version),
        analysis_enabled=True,
        eager=eager,
        preload=(not no_preload),
    )

    build_sitemap_endpoint(app)
    build_synchronous_compiler_service(app, manager=manager)
    build_pickle_uploader_service(app, manager=manager)
    build_analysis_service(app, manager=manager, api=api)
    build_curation_service(app)
    build_reporting_service(app, manager=manager)

    if run_database_service:
        build_database_service(app, manager)

    if run_parser_service or run_all:
        build_parser_service(app)

    if run_receiver_service or run_all:
        build_receiver_service(app, manager=manager)

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
@click.option('-c', '--connection', help='Cache connection. Defaults to {}'.format(get_cache_connection()))
@click.option('-p', '--path', type=click.File('r'), default=sys.stdin, help='Input BEL file path. Defaults to stdin.')
@click.option('-d', '--directory', help='Output directory. Defaults to current working directory')
def serialize_namespaces(namespaces, connection, path, directory):
    """Parses a BEL document then serializes the given namespaces (errors and all) to the given directory"""
    graph = from_lines(path, manager=connection)
    export_namespaces(namespaces, graph, directory)


@main.group()
def manage():
    """Manage database"""


@manage.group()
def user():
    """Manage users"""


@user.command()
@click.option('-c', '--connection', help='Cache connection. Defaults to {}'.format(get_cache_connection()))
def ls(connection):
    manager = build_manager(connection)
    for u in manager.session.query(User).all():
        click.echo('{}\t{}\t{}'.format(u.id, u.email, ','.join(r.name for r in u.roles)))


@user.command()
@click.argument('user_id')
@click.option('-c', '--connection', help='Cache connection. Defaults to {}'.format(get_cache_connection()))
def add_admin(user_id, connection):
    """Adds admin privileges to a given account"""
    manager = build_manager(connection)
    u = manager.session.query(User).get(user_id)
    r = manager.session.query(Role).filter(Role.name == PYBEL_ADMIN_ROLL_NAME).one()
    u.roles.append(r)
    manager.session.commit()


@manage.group()
def role():
    """Manage roles"""


@role.command()
@click.argument('name')
@click.option('-d', '--description')
@click.option('-c', '--connection', help='Cache connection. Defaults to {}'.format(get_cache_connection()))
def add_role(name, description, connection):
    """Creates a new role"""
    manager = build_manager(connection)
    try:
        r = Role(name=name, description=description)
        manager.session.add(r)
        manager.session.commit()
    except:
        manager.rollback()


@role.command()
@click.option('-c', '--connection', help='Cache connection. Defaults to {}'.format(get_cache_connection()))
def ls(connection):
    manager = build_manager(connection)
    for r in manager.session.query(Role).all():
        click.echo('{}\t{}\t{}'.format(r.id, r.name, r.description))


if __name__ == '__main__':
    main()
