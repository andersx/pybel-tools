# -*- coding: utf-8 -*-

import logging
import re

from flask import render_template, make_response
from flask_wtf import FlaskForm
from six import StringIO
from wtforms import fields
from wtforms.validators import DataRequired, Email

from pybel_tools.document_utils import write_boilerplate

log = logging.getLogger(__name__)


class BoilerplateForm(FlaskForm):
    name = fields.StringField('Document Name', validators=[DataRequired()])
    description = fields.StringField('Document Description', validators=[DataRequired()])
    authors = fields.StringField('Authors', validators=[DataRequired()])
    contact_email = fields.StringField('Contact Email', validators=[DataRequired(), Email()])
    pmids = fields.StringField('PubMed Identifiers, separated by commas')
    licenses = fields.RadioField(
        'License',
        choices=[
            ('CC BY 4.0', 'Add the CC BY 4.0 license'),
            ('Other/Proprietary', 'Add an "Other/Proprietary" license')
        ],
        default='CC BY 4.0'
    )
    submit = fields.SubmitField('Generate')


def build_boilerplate_service(app):
    """Adds the boilerplate BEL script generator to the app
    
    :param Flask app: A Flask App
    """

    @app.route('/boilerplate', methods=['GET', 'POST'])
    def get_boilerplate():
        """Serves a boilerplate BEL document"""
        form = BoilerplateForm()

        if not form.validate_on_submit():
            return render_template('boilerplate.html', form=form)

        si = StringIO()

        pmids = [int(x.strip()) for x in form.pmids.data.split(',') if x]

        write_boilerplate(
            document_name=form.name.data,
            contact=form.contact_email.data,
            description=form.description.data,
            authors=form.authors.data,
            licenses=form.licenses.data,
            pmids=pmids,
            file=si
        )

        identifier = re.sub(r"\s+", '_', form.name.data.lower())

        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = "attachment; filename={}.bel".format(identifier)
        output.headers["Content-type"] = "text/plain"
        return output

    log.info('added boilerplate generator service')
