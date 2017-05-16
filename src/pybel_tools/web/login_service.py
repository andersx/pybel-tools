# -*- coding: utf-8 -*-

import logging
import os

import flask
import requests
from flask import Response, redirect, url_for, request, session, jsonify, flash
from flask_github import GitHub
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user

from .constants import PYBEL_GITHUB_CLIENT_ID, PYBEL_GITHUB_CLIENT_SECRET

login_log = logging.getLogger('pybel.web.login')


def get_github_info(token):
    return requests.get('https://api.github.com/user', params={'access_token': token}).json()


administrator_usernames = {'cthoyt', 'ddomingof', 'cebel'}


class User(UserMixin):
    def __init__(self, github_access_token):
        self.id = github_access_token
        info = get_github_info(github_access_token)
        self.username = info['login']
        self.name = info['name']
        self.user_id = int(info['id'])

    def __repr__(self):
        return self.id

    @property
    def admin(self):
        return self.username in administrator_usernames

    @property
    def display(self):
        return self.name if self.name else self.username


def build_login_service(app):
    """Adds the login service
    
    Before adding this service, both ``GITHUB_CLIENT_ID`` and ``GITHUB_CLIENT_SECRET`` need to be set in the app's
    configuration
    
    :param flask.Flask app: A Flask app
    """
    app.config.update({
        'GITHUB_CLIENT_ID': os.environ[PYBEL_GITHUB_CLIENT_ID],
        'GITHUB_CLIENT_SECRET': os.environ[PYBEL_GITHUB_CLIENT_SECRET]
    })

    # flask-login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    # setup github-flask
    github = GitHub(app)

    @github.access_token_getter
    def token_getter():
        if current_user is not None:
            return current_user.id

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if session.get('user_id', None) is None:
            return github.authorize()
        else:
            flask.flash('Already logged in')
            return redirect(url_for('index'))

    @app.route('/github-callback')
    @github.authorized_handler
    def authorized(access_token):
        next_url = request.args.get('next') or url_for('view_networks')
        if access_token is None:
            return redirect(next_url)

        user = User(access_token)

        if app.config.get('PYBEL_WEB_STRICT_LOGIN') and not user.name:
            flash('Please add your name to your GitHub account to use PyBEL Web')
            return redirect(url_for('index'))

        login_user(user)
        login_log.info('Login from %s by %s (%s)', request.remote_addr, user.name, user.username)

        return redirect(next_url)

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('Logged out')
        return redirect(url_for('view_networks'))

    @app.errorhandler(401)
    def page_not_found(e):
        return Response('<p>Login failed</p>')

    # callback to reload the user object
    @login_manager.user_loader
    def load_user(id):
        return User(id)

    @app.route('/user')
    @login_required
    def show_user():
        return jsonify(github.get('user'))
