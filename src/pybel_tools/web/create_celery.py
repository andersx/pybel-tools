# -*- encoding: utf-8 -*-

"""
Resources:

1. https://citizen-stig.github.io/2016/02/17/using-celery-with-flask-factories.html
2. https://github.com/citizen-stig/celery-with-flask-factories
3. https://blog.miguelgrinberg.com/post/celery-and-the-flask-application-factory-pattern
4. http://flask.pocoo.org/docs/0.12/patterns/celery/
"""

from celery import Celery


def create_celery(application):
    """Configures celery instance from application, using its config
    
    :param flask.Flask application: Flask application instance
    :return: A Celery instance
    :rtype: celery.Celery
    """
    celery = Celery(application.import_name, broker=application.config['CELERY_BROKER_URL'])
    celery.conf.update(application.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with application.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery
