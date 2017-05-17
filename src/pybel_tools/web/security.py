# -*- coding: utf-8 -*-

import logging

import flask
from flask import redirect
from flask import url_for
from flask_security import Security, SQLAlchemyUserDatastore, \
    UserMixin, RoleMixin, login_required
from sqlalchemy import Table, Integer, Column, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship, backref

from pybel.manager.models import Base

login_log = logging.getLogger('pybel.web.login')

# Define models
roles_users = Table('roles_users', Base.metadata,
                    Column('user_id', Integer, ForeignKey('user.id')),
                    Column('role_id', Integer, ForeignKey('role.id')))


class Role(Base, RoleMixin):
    """Stores user roles"""
    id = Column(Integer(), primary_key=True)
    name = Column(String(80), unique=True)
    description = Column(String(255))


class User(Base, UserMixin):
    """Stores users"""
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True)
    password = Column(String(255))
    active = Column(Boolean)
    confirmed_at = Column(DateTime)
    roles = relationship('Role', secondary=roles_users,
                         backref=backref('users', lazy='dynamic'))


def build_flask_security_app(app, manager):
    """Builds the Flask-Security Login Protocol

    :param flask.Flask app: 
    :param pybel.manager.cache.CacheManager manager: 
    :return: 
    """
    user_datastore = SQLAlchemyUserDatastore(manager, User, Role)
    Security(app, user_datastore)

    # Create a user to test with
    @app.before_first_request
    def create_user():
        manager.create_all()
        user_datastore.create_user(email='matt@nobien.net', password='password')
        manager.session.commit()

    # Views
    @app.route('/')
    @login_required
    def home():
        return redirect(url_for('index'))
