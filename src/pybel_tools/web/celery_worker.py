# -*- coding: utf-8 -*-

import datetime
import logging

import requests.exceptions
from celery.schedules import crontab
from celery.schedules import schedule
from celery.utils.log import get_task_logger
from flask_mail import Message
from sqlalchemy.exc import IntegrityError

from pybel import from_lines
from pybel.constants import PYBEL_CONNECTION
from pybel.manager import build_manager
from pybel.parser.parse_exceptions import InconsistientDefinitionError
from .application import create_application
from .constants import integrity_message
from .create_celery import create_celery
from .models import Report
from .models import get_recent_reports
from ..mutation import add_canonical_names

app, mail = create_application(get_mail=True)
celery = create_celery(app)

log = get_task_logger(__name__)


@celery.task(name='pybelparser')
def async_parser(lines, connection, current_user_id, current_user_email, public, allow_nested=False,
                 citation_clearing=False, store_parts=False):
    """Asynchronously parses a BEL script and sends email feedback"""
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
        with app.app_context():
            mail.send(Message(
                subject='Parsing Failed',
                recipients=[current_user_email],
                body=message,
                sender=("PyBEL Web", 'pybel@scai.fraunhofer.de'),
            ))
        return message
    except InconsistientDefinitionError as e:
        message = '{} was defined multiple times.'.format(e.definition)
        log.exception(message)
        with app.app_context():
            mail.send(Message(
                subject='Parsing Failed',
                recipients=[current_user_email],
                body=message,
                sender=("PyBEL Web", 'pybel@scai.fraunhofer.de'),
            ))
        return message
    except Exception as e:
        message = 'Compilation error: {}'.format(e)
        log.exception(message)
        with app.app_context():
            mail.send(Message(
                subject='Parsing Failed',
                recipients=[current_user_email],
                body=message,
                sender=("PyBEL Web", 'pybel@scai.fraunhofer.de'),
            ))
        return message

    try:
        network = manager.insert_graph(graph, store_parts=store_parts)
    except IntegrityError:
        message = integrity_message.format(graph.name, graph.version)
        log.exception(message)
        manager.rollback()
        with app.app_context():
            mail.send(Message(
                subject='Upload Failed',
                recipients=[current_user_email],
                body=message,
                sender=("PyBEL Web", 'pybel@scai.fraunhofer.de'),
            ))
        return message
    except Exception as e:
        message = "Error storing in database: {}".format(e)
        log.exception(message)
        with app.app_context():
            mail.send(Message(
                subject='Upload Failed',
                recipients=[current_user_email],
                body=message,
                sender=("PyBEL Web", 'pybel@scai.fraunhofer.de'),
            ))
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
        mail.send(Message(
            subject='Parsing complete',
            recipients=[current_user_email],
            body='{} is done parsing.'.format(graph),
            sender=("PyBEL Web", 'pybel@scai.fraunhofer.de'),
        ))

    return network.id


@celery.task(name='reportuploads')
def report_activity(connection, recipient):
    """Sends a report of recent activity"""
    manager = build_manager(connection)

    with app.app_context():
        mail.send(Message(
            subject='PyBEL Web Activty Report',
            recipients=[recipient],
            body='\n'.join(get_recent_reports(manager, weeks=1)),
            sender=("PyBEL Web", 'pybel@scai.fraunhofer.de'),
        ))

    log.info('Sent report to %s', recipient)


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Sets up the periodic tasks to be run asynchronously by Celery"""
    recipient = app.config.get('PYBEL_WEB_REPORT_RECIPIENT')
    log.warning('Recipeint value: %s', recipient)

    if recipient:
        #sender.add_periodic_task(
        #    crontab(day_of_week=1),
        #    report_activity.s(app.config.get(PYBEL_CONNECTION), recipient),
        #)

        sender.add_periodic_task(
            60.0,
            report_activity.s(app.config.get(PYBEL_CONNECTION), recipient),
        )


if __name__ == '__main__':
    logging.basicConfig(level=20)
    log.setLevel(20)
