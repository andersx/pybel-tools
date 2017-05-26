# -*- coding: utf-8 -*-

import requests.exceptions
from celery.utils.log import get_task_logger
from flask_login import current_user
from sqlalchemy.exc import IntegrityError

from pybel import from_lines
from pybel.manager import build_manager
from pybel.parser.parse_exceptions import InconsistientDefinitionError
from pybel_tools.mutation import add_canonical_names
from .application import create_application
from .celery import create_celery
from .constants import integrity_message
from .models import log_graph, add_network_reporting

app = create_application()
celery = create_celery(app)

log = get_task_logger(__name__)


# TODO add email notification

@celery.task(name='pybelparser')
def async_parser(lines, connection, allow_nested=False, citation_clearing=False, store_parts=False):
    log.info('starting parsing')
    manager = build_manager(connection)
    try:
        graph = from_lines(
            lines,
            manager=manager,
            allow_nested=allow_nested,
            citation_clearing=citation_clearing
        )
        add_canonical_names(graph)
    except requests.exceptions.ConnectionError as e:
        message = 'Connection to resource could not be established.'
        log.exception(message)
        return message
    except InconsistientDefinitionError as e:
        message = '{} was defined multiple times.'.format(e.definition)
        log.exception(message)
        return message
    except Exception as e:
        message = 'Compilation error: {}'.format(e)
        log.exception(message)
        return message

    try:
        network = manager.insert_graph(graph, store_parts=store_parts)
    except IntegrityError:
        log_graph(graph, current_user, preparsed=False, failed=True)
        message = integrity_message.format(graph.name, graph.version)
        log.exception(message)
        manager.rollback()
        return message
    except Exception as e:
        log_graph(graph, current_user, preparsed=False, failed=True)
        message = "Error storing in database: {}".format(e)
        log.exception(message)
        return message

    log.info('done storing [%d]', network.id)

    try:
        add_network_reporting(manager, network, current_user, graph.number_of_nodes(), graph.number_of_edges(),
                              len(graph.warnings), preparsed=False)
    except IntegrityError:
        message = 'Problem with reporting service.'
        log.exception(message)
        manager.rollback()
        return message

    return network.id

