# -*- coding: utf-8 -*-

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import fields
from wtforms.fields import BooleanField, RadioField, HiddenField
from wtforms.validators import DataRequired, Email

from ..selection.induce_subgraph import SEED_TYPE_INDUCTION, SEED_TYPE_PATHS, SEED_TYPE_NEIGHBORS, \
    SEED_TYPE_DOUBLE_NEIGHBORS


class UploadForm(FlaskForm):
    """Builds an upload form with wtf-forms"""
    file = FileField('A PyBEL gpickle', validators=[
        DataRequired(message="You must provide a PyBEL gpickle file"),
        FileAllowed(['gpickle'], 'Only gpickles allowed')
    ])
    name = fields.StringField('Your Name', validators=[DataRequired()])
    email = fields.StringField('Your Email Address', validators=[DataRequired(), Email()])
    submit = fields.SubmitField('Upload')


class SeedSubgraphForm(FlaskForm):
    """Builds the form for seeding by subgraph"""
    node_list = HiddenField('Nodes')
    seed_method = fields.RadioField(
        'Expansion Method',
        choices=[
            (SEED_TYPE_INDUCTION, 'Induce a subgraph over the given nodes'),
            (SEED_TYPE_NEIGHBORS, 'Induce a subgraph over the given nodes and expand to their first neighbors'),
            (SEED_TYPE_DOUBLE_NEIGHBORS, 'Induce a subgraph over the given nodes and expand to their second neighbors'),
            (SEED_TYPE_PATHS, 'Induce a subgraph over the nodes in all shortest paths between the given nodes'),
        ],
        default=SEED_TYPE_INDUCTION)
    filter_pathologies = BooleanField('Filter pathology nodes', default=True)
    submit_subgraph = fields.SubmitField('Submit Subgraph')


class SeedProvenanceForm(FlaskForm):
    """Builds the form for seeding by author/citation"""
    author_list = HiddenField('Nodes')
    pubmed_list = HiddenField('Nodes')
    filter_pathologies = BooleanField('Filter pathology nodes', default=True)
    submit_provenance = fields.SubmitField('Submit Provenance')


class CompileForm(FlaskForm):
    """Builds an upload form with wtf-forms"""
    file = FileField('My BEL file', validators=[DataRequired()])
    name = fields.StringField('Your Name', validators=[DataRequired()])
    email = fields.StringField('Your Email Address', validators=[DataRequired(), Email()])
    suggest_name_corrections = BooleanField('Suggest name corrections')
    suggest_naked_name = BooleanField('My document contains unqualified names - suggest appropriate namespaces')
    allow_nested = BooleanField('My document contains nested statements')
    citation_clearing = BooleanField("My document sometimes has evidences before citations - disable citation clearing")
    save_network = BooleanField('Save my network for later viewing')
    save_edge_store = BooleanField('Save my network and cache in edge store for querying and exploration')
    encoding = RadioField(
        'Encoding',
        choices=[
            ('utf-8', 'My document is encoded in UTF-8'),
            ('utf_8_sig', 'My document is encoded in UTF-8 with a BOM')
        ],
        default='utf-8')
    submit = fields.SubmitField('Validate')


class DifferentialGeneExpressionForm(FlaskForm):
    """Builds the form for uploading differential gene expression data"""
    file = FileField('Differential gene expression file', validators=[DataRequired()])
    gene_symbol_column = fields.StringField('Gene Symbol Column Name', default='Gene.symbol')
    log_fold_change_column = fields.StringField('Log Fold Change Column Name', default='logFC')
    permutations = fields.IntegerField('Number of permutations', default=100)
    description = fields.StringField('Description of data', validators=[DataRequired()])
    separator = RadioField(
        'Separator',
        choices=[
            ('\t', 'My document is a TSV file'),
            (',', 'My document is a CSV file'),
        ],
        default='\t')
    submit = fields.SubmitField('Analyze')
