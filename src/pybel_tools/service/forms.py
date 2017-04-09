# -*- coding: utf-8 -*-

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import fields
from wtforms.validators import DataRequired


class UploadPickleForm(FlaskForm):
    """Builds an upload form with wtf-forms"""
    file = FileField('A PyBEL gpickle', validators=[
        DataRequired(),
        FileAllowed(['gpickle'], 'Only gpickles allowed')
    ])
    submit = fields.SubmitField('Upload')
