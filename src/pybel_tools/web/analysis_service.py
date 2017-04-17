# -*- coding: utf-8 -*-

import logging

import flask
import pandas
import pandas as pd
from flask import render_template

import pybel
from pybel.constants import GENE
from pybel.manager.models import Network
from .forms import DifferentialGeneExpressionForm
from .. import generation
from ..analysis import npa
from ..integration import overlay_type_data
from ..mutation.collapse import opening_on_central_dogma, collapse_variants_to_genes
from ..mutation.deletion import remove_nodes_by_namespace

log = logging.getLogger(__name__)

LABEL = 'dgxa'


def build_analysis_service(app, manager):
    """
    
    :param app: A Flask application
    :type app: flask.Flask
    :param manager: A PyBEL cache manager
    :type manager: pybel.manager.cache.CacheManager
    """

    @app.route('/analysis/<int:network_id>', methods=('GET', 'POST'))
    def view_analysis(network_id):
        """Views the results of analysis on a given graph"""
        form = DifferentialGeneExpressionForm()

        if not form.validate_on_submit():
            name, = manager.session.query(Network.name).filter(Network.id == network_id).one()
            return render_template('analyze_dgx.html', form=form, network_name=name)

        log.info('Analyzing %s', form.file.data.filename)

        df = pandas.read_csv(form.file.data)

        gene_column = form.gene_symbol_column.data
        data_column = form.log_fold_change_column.data

        if gene_column not in df.columns:
            raise ValueError('{} not a column in document'.format(gene_column))

        if data_column not in df.columns:
            raise ValueError('{} not a column in document'.format(data_column))

        df = df.loc[df[gene_column].notnull(), [gene_column, data_column]]

        data = {k: v for _, k, v in df.itertuples()}

        graph = pybel.from_bytes(manager.get_graph_by_id(network_id).blob)

        remove_nodes_by_namespace(graph, {'MGI', 'RGD'})
        opening_on_central_dogma(graph)
        collapse_variants_to_genes(graph)

        overlay_type_data(graph, data, LABEL, GENE, 'HGNC', overwrite=False, impute=0)

        candidate_mechanisms = generation.generate_bioprocess_mechanisms(graph, LABEL)
        scores = npa.calculate_average_npa_on_subgraphs(candidate_mechanisms, LABEL, runs=form.permutations.data)
        scores_df = pd.DataFrame.from_items(scores.items(),
                                            orient='index',
                                            columns=['NPA Average', 'NPA Standard Deviation', 'NPA Median',
                                                     'Number First Neighbors', 'Subgraph Size'])

        return scores_df.sort_values('NPA Average').to_html()

    log.info('Added analysis service to %s', app)
