# -*- coding: utf-8 -*-


class Config:
    """This is the default configuration to be used in a development environment. It assumes you have:
    
    - SQLite for the PyBEL Cache
    - RabbitMQ or another message broker supporting the AMQP protocol
    """
    DEBUG = False
    TESTING = False
    SECRET_KEY = 'pybel_default_key'

    CELERY_BROKER_URL = 'amqp://localhost'

    SECURITY_REGISTERABLE = True
    SECURITY_CONFIRMABLE = False
    SECURITY_SEND_REGISTER_EMAIL = False
    SECURITY_PASSWORD_HASH = 'pbkdf2_sha512'
    SECURITY_PASSWORD_SALT = 'pybel_default_salt'

    PYBEL_CONNECTION = None
    PYBEL_DS_CHECK_VERSION = True
    PYBEL_DS_EAGER = False
    PYBEL_DS_PRELOAD = False
