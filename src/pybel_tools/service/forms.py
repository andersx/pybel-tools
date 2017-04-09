# -*- coding: utf-8 -*-

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import fields
from wtforms.validators import DataRequired

from ..selection.induce_subgraph import SEED_TYPE_INDUCTION, SEED_TYPE_PATHS, SEED_TYPE_NEIGHBORS


class UploadPickleForm(FlaskForm):
    """Builds an upload form with wtf-forms"""
    file = FileField('A PyBEL gpickle', validators=[
        DataRequired(),
        FileAllowed(['gpickle'], 'Only gpickles allowed')
    ])
    submit = fields.SubmitField('Upload')


class SeedSubgraphForm(FlaskForm):
    """Builds the form for seeding by subgraph"""
    node_list = fields.StringField('Nodes')
    seed_method = fields.RadioField(
        'Expansion Method',
        choices=[
            (SEED_TYPE_INDUCTION, 'Induce a subgraph over the given nodes'),
            (SEED_TYPE_NEIGHBORS, 'Induce a subgraph over the given nodes and expand to their first neighbors'),
            (SEED_TYPE_PATHS, 'Induce a subgraph over the nodes in all shortest paths between the given nodes'),
        ],
        default=SEED_TYPE_INDUCTION)
    submit_subgraph = fields.SubmitField('Submit Subgraph')


class SeedProvenanceForm(FlaskForm):
    """Builds the form for seeding by author/citation"""
    author_list = fields.StringField('Authors')
    pubmed_list = fields.StringField('PubMed Identifiers')
    submit_provenance = fields.SubmitField('Submit Provenance')
