# -*- coding: utf-8 -*-

import logging

import flask
from flask import redirect, url_for, jsonify, render_template
from flask_security import Security, SQLAlchemyUserDatastore, \
    UserMixin, RoleMixin, roles_required
from flask_security.forms import RegisterForm, get_form_field_label
from sqlalchemy import Table, Integer, Column, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship, backref
from wtforms.fields import StringField, SubmitField
from wtforms.validators import DataRequired

from pybel.manager.models import Base
from .extension import get_manager

log = logging.getLogger(__name__)
login_log = logging.getLogger('pybel.web.login')

PYBEL_WEB_ROLE_TABLE = 'pybel_role'
PYBEL_WEB_USER_TABLE = 'pybel_user'
PYBEL_ADMIN_ROLE_NAME = 'admin'

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

    def __str__(self):
        return self.name


class User(Base, UserMixin):
    """Stores users"""
    __tablename__ = PYBEL_WEB_USER_TABLE
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True)
    password = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    active = Column(Boolean)
    confirmed_at = Column(DateTime)
    roles = relationship('Role', secondary=roles_users, backref=backref('users', lazy='dynamic'))

    @property
    def admin(self):
        """Is this user an administrator?"""
        return self.has_role('admin')

    @property
    def name(self):
        return '{} {}'.format(self.first_name, self.last_name) if self.first_name else self.email

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return '<User {}>'.format(self.email)


class ExtendedRegisterForm(RegisterForm):
    first_name = StringField('First Name', [DataRequired()])
    last_name = StringField('Last Name', [DataRequired()])
    submit = SubmitField(get_form_field_label('register'))


def build_security_service(app):
    """Builds the Flask-Security Login Protocol

    :param flask.Flask app: 
    :return: The instance of the user data store object
    :rtype: SQLAlchemyUserDatastore
    """
    manager = get_manager(app)
    user_datastore = SQLAlchemyUserDatastore(manager, User, Role)
    Security(app, user_datastore, register_form=ExtendedRegisterForm)

    @app.before_first_request
    def create_user():
        manager.create_all()
        user_datastore.find_or_create_role(name='admin', description='Administrator of PyBEL Web')
        user_datastore.find_or_create_role(name='scai', description='Users of PyBEL Web from Fraunhofer SCAI')
        manager.session.commit()

    @app.route('/wrap/logout')
    def logout():
        return redirect(url_for('security.logout'))

    @app.route('/wrap/login')
    def login():
        return redirect(url_for('security.login'))

    @app.route('/admin/user/<user>/add_role/<role>')
    @roles_required('admin')
    def add_user_role(user, role):
        user_datastore.add_role_to_user(user, role)
        user_datastore.commit()
        return jsonify({'status': 200})

    @app.route('/admin/user/<user>/remove_role/<role>')
    @roles_required('admin')
    def remove_user_role(user, role):
        user_datastore.remove_role_from_user(user, role)
        user_datastore.commit()
        return jsonify({'status': 200})

    @app.route('/admin/user/list')
    @roles_required('admin')
    def list_users():
        return jsonify(manager.session.query(User).all())

    @app.route('/users')
    @roles_required('admin')
    def view_users():
        return render_template('view_users.html', users=manager.session.query(User).all())

    @app.route('/api/user/<int:user_id>/delete')
    @roles_required('admin')
    def delete_user(user_id):
        """Deletes a user"""
        u = User.query.get(user_id)
        user_datastore.delete_user(u)
        user_datastore.commit()
        return jsonify({'status': 200, 'action': 'deleted user', 'user': str(u)})

    log.info('built security service')

    return user_datastore
