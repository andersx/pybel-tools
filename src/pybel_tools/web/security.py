# -*- coding: utf-8 -*-

import logging

import flask
from flask import redirect
from flask import url_for
from flask_security import Security, SQLAlchemyUserDatastore, \
    UserMixin, RoleMixin
from flask_security.forms import RegisterForm, get_form_field_label
from sqlalchemy import Table, Integer, Column, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship, backref
from wtforms.fields import StringField, SubmitField
from wtforms.validators import DataRequired

from pybel.manager.models import Base

login_log = logging.getLogger('pybel.web.login')

PYBEL_WEB_ROLE_TABLE = 'pybel_role'
PYBEL_WEB_USER_TABLE = 'pybel_user'
PYBEL_ADMIN_ROLL_NAME = 'admin'

# Define models
roles_users = Table('roles_users', Base.metadata,
                    Column('user_id', Integer, ForeignKey('{}.id'.format(PYBEL_WEB_USER_TABLE))),
                    Column('role_id', Integer, ForeignKey('{}.id'.format(PYBEL_WEB_ROLE_TABLE))))


class Role(Base, RoleMixin):
    """Stores user roles"""
    __tablename__ = PYBEL_WEB_ROLE_TABLE
    id = Column(Integer(), primary_key=True)
    name = Column(String(80), unique=True)
    description = Column(String(255))


class User(Base, UserMixin):
    """Stores users"""
    __tablename__ = PYBEL_WEB_USER_TABLE
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True)
    password = Column(String(255))
    active = Column(Boolean)
    confirmed_at = Column(DateTime)
    roles = relationship('Role', secondary=roles_users,
                         backref=backref('users', lazy='dynamic'))

    @property
    def display(self):
        return self.email

    @property
    def admin(self):
        return self.has_role(PYBEL_ADMIN_ROLL_NAME)


class ExtendedRegisterForm(RegisterForm):
    first_name = StringField('First Name', [DataRequired()])
    last_name = StringField('Last Name', [DataRequired()])
    submit = SubmitField(get_form_field_label('register'))


def build_security_service(app, manager):
    """Builds the Flask-Security Login Protocol

    :param flask.Flask app: 
    :param pybel.manager.cache.CacheManager manager: 
    :return: 
    """
    user_datastore = SQLAlchemyUserDatastore(manager, User, Role)
    Security(app, user_datastore, register_form=ExtendedRegisterForm)

    @app.before_first_request
    def create_user():
        try:
            manager.create_all()
            user_datastore.create_user(email='guest@scai.fraunhofer.de', password='guest')
            user_datastore.create_role(name=PYBEL_ADMIN_ROLL_NAME, description='Administrator of PyBEL Web')
            manager.session.commit()
        except:
            manager.session.rollback()

    @app.route('/wrap/logout')
    def logout():
        return redirect(url_for('security.logout'))

    @app.route('/wrap/login')
    def login():
        return redirect(url_for('security.login'))
