# -*- coding: utf-8 -*-

import codecs
import logging

from flask import render_template, request, make_response
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from six import StringIO
from wtforms import fields
from wtforms.validators import DataRequired, Email

from pybel.constants import NAMESPACE_DOMAIN_TYPES
from pybel.utils import parse_bel_resource
from ..definition_utils import write_namespace

log = logging.getLogger(__name__)


class MergeNamespaceForm(FlaskForm):
    """Builds a form for merging namespace files"""
    file = FileField('BEL Namespace Files', render_kw={'multiple': True}, validators=[
        DataRequired(),
        FileAllowed(['belns'], 'Only files with the *.belns extension are allowed')
    ])
    name = fields.StringField('Name', validators=[DataRequired()])
    keyword = fields.StringField('Keyword', validators=[DataRequired()])
    description = fields.StringField('Description', validators=[DataRequired()])
    domain = fields.RadioField('Domain', choices=[(x, x) for x in sorted(NAMESPACE_DOMAIN_TYPES)])
    authors = fields.StringField('Authors', validators=[DataRequired()])
    contact_email = fields.StringField('Contact Email', validators=[DataRequired(), Email()])
    citation = fields.StringField('Citation Name', validators=[DataRequired()])
    species = fields.StringField('Species', validators=[DataRequired()], default='9606')
    licenses = fields.RadioField(
        'License',
        choices=[
            ('CC BY 4.0', 'Add the CC BY 4.0 license'),
            ('Other/Proprietary', 'Add an "Other/Proprietary" license')
        ],
        default='CC BY 4.0'
    )
    submit = fields.SubmitField('Merge')


def build_merge_service(app):
    """Adds the endpoint for merging BEL namespcaes

    :param flask.Flask app: A Flask application
    """

    @app.route('/curation/namespace/merge', methods=['GET', 'POST'])
    def merge_namespaces():
        """Serves the page for merging bel namespaces"""
        form = MergeNamespaceForm()

        if not form.validate_on_submit():
            return render_template('merge_namespaces.html', form=form)

        log.warning(form.file)

        files = request.files.getlist("file")

        names = set()

        for file in files:
            log.warning('file: %s', file)
            lines = list(codecs.iterdecode(file, 'utf-8'))
            for line in lines:
                print(line)
            resource = parse_bel_resource(lines)
            names |= set(resource['Values'])

        si = StringIO()

        write_namespace(
            namespace_name=form.name.data,
            namespace_keyword=form.keyword.data,
            namespace_species=form.species.data,
            namespace_description=form.description.data,
            author_name=form.authors.data,
            citation_name=form.citation.data,
            citation_description='This namespace was created by the PyBEL Web namespace merge service',
            namespace_domain=form.domain.data,
            author_copyright=form.licenses.data,
            values=names,
            cacheable=False,
            file=si
        )

        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = "attachment; filename={}.belns".format(form.keyword.data)
        output.headers["Content-type"] = "text/csv"
        return output
