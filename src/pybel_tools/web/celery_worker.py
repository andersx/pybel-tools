# -*- coding: utf-8 -*-

import requests.exceptions
from celery.utils.log import get_task_logger
from flask import url_for
from flask_mail import Message
from sqlalchemy.exc import IntegrityError

from pybel import from_lines
from pybel.manager import build_manager
from pybel.parser.parse_exceptions import InconsistientDefinitionError
from pybel_tools.mutation import add_canonical_names
from .application import create_application
from .celery import create_celery
from .constants import integrity_message
from .models import Report

app, mail = create_application(get_mail=True)
celery = create_celery(app)

log = get_task_logger(__name__)


# TODO add email notification

@celery.task(name='pybelparser')
def async_parser(lines, connection, current_user_id, current_user_email, public, allow_nested=False,
                 citation_clearing=False, store_parts=False):
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
        message = integrity_message.format(graph.name, graph.version)
        log.exception(message)
        manager.rollback()
        return message
    except Exception as e:
        message = "Error storing in database: {}".format(e)
        log.exception(message)
        return message

    log.info('done storing [%d]', network.id)

    try:
        report = Report(
            network=network,
            user_id=current_user_id,
            number_nodes=graph.number_of_nodes(),
            number_edges=graph.number_of_edges(),
            number_warnings=len(graph.warnings),
            public=public,
        )
        manager.session.add(report)
        manager.session.commit()
    except IntegrityError:
        message = 'Problem with reporting service.'
        log.exception(message)
        manager.rollback()
        return message

    with app.app_context():
        completion_msg = Message(
            subject='Parsing complete',
            recipients=[current_user_email],
            body='{} is done parsing.'.format(graph),
            sender=("PyBEL Web", 'pybel@scai.fraunhofer.de'),
        )

        mail.send(completion_msg)

    return network.id
