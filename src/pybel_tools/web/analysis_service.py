# -*- coding: utf-8 -*-

import datetime
import logging
import pickle
from operator import itemgetter

import flask
import pandas
from flask import render_template, redirect, url_for, jsonify
from sqlalchemy import Column, Integer, DateTime, Binary, Text, ForeignKey
from sqlalchemy.orm import relationship

import pybel
from pybel.constants import GENE
from pybel.manager.models import Base, Network, NETWORK_TABLE_NAME
from .dict_service import get_graph_from_request
from .forms import DifferentialGeneExpressionForm
from .. import generation
from ..analysis import npa
from ..filters.node_deletion import remove_nodes_by_namespace
from ..integration import overlay_type_data
from ..mutation.collapse import collapse_variants_to_genes, collapse_by_central_dogma_to_genes

log = logging.getLogger(__name__)

PYBEL_EXPERIMENT_TABLE_NAME = 'pybel_experiment'
PYBEL_EXPERIMENT_ENTRY_TABLE_NAME = 'pybel_experiment_entry'

LABEL = 'dgxa'


class Experiment(Base):
    """Represents a Candidate Mechanism Perturbation Amplitude experiment run in PyBEL Web"""
    __tablename__ = PYBEL_EXPERIMENT_TABLE_NAME

    id = Column(Integer, primary_key=True)

    created = Column(DateTime, default=datetime.datetime.utcnow, doc='The date on which this analysis was run')
    description = Column(Text, nullable=True, doc='A description of the purpose of the analysis')
    permutations = Column(Integer, doc='Number of permutations performed')
    source_name = Column(Text, doc='The name of the source file')
    source = Column(Binary, doc='The source document holding the data')
    result = Column(Binary, doc='The result python dictionary')

    network_id = Column(Integer, ForeignKey('{}.id'.format(NETWORK_TABLE_NAME)))
    network = relationship('Network', foreign_keys=[network_id])

    @property
    def data(self):
        """Get unpickled data"""
        return pickle.loads(self.result)


def build_analysis_service(app, manager, api):
    """Builds the analysis service
    
    :param app: A Flask application
    :type app: flask.Flask
    :param manager: A PyBEL cache manager
    :type manager: pybel.manager.CacheManager
    :param DictionaryService api: The dictionary service API
    """

    @app.route('/analysis/')
    def view_analyses():
        """Views a list of all analyses"""
        experiments = manager.session.query(Experiment).all()
        return render_template('analysis_list.html', experiments=experiments)

    @app.route('/analysis/results/<analysis_id>')
    def view_analysis_results(analysis_id):
        """View the results of a given analysis"""
        experiment = manager.session.query(Experiment).get(analysis_id)
        return render_template(
            'analysis_results.html',
            experiment=experiment,
            columns=npa.RESULT_LABELS,
            data=sorted([(k, v) for k, v in experiment.data.items() if v[0]], key=itemgetter(1))
        )

    @app.route('/analysis/upload/<int:network_id>', methods=('GET', 'POST'))
    def view_analysis_uploader(network_id):
        """Views the results of analysis on a given graph"""
        form = DifferentialGeneExpressionForm()

        if not form.validate_on_submit():
            name, = manager.session.query(Network.name).filter(Network.id == network_id).one()
            return render_template('analyze_dgx.html', form=form, network_name=name)

        log.info('Analyzing %s: %s', form.file.data.filename, form.description.data)

        df = pandas.read_csv(form.file.data)

        gene_column = form.gene_symbol_column.data
        data_column = form.log_fold_change_column.data

        if gene_column not in df.columns:
            raise ValueError('{} not a column in document'.format(gene_column))

        if data_column not in df.columns:
            raise ValueError('{} not a column in document'.format(data_column))

        df = df.loc[df[gene_column].notnull(), [gene_column, data_column]]

        data = {k: v for _, k, v in df.itertuples()}

        network = manager.get_graph_by_id(network_id)
        graph = pybel.from_bytes(network.blob)

        remove_nodes_by_namespace(graph, {'MGI', 'RGD'})
        collapse_by_central_dogma_to_genes(graph)
        collapse_variants_to_genes(graph)

        overlay_type_data(graph, data, LABEL, GENE, 'HGNC', overwrite=False, impute=0)

        candidate_mechanisms = generation.generate_bioprocess_mechanisms(graph, LABEL)
        scores = npa.calculate_average_npa_on_subgraphs(candidate_mechanisms, LABEL, runs=form.permutations.data)

        experiment = Experiment(
            description=form.description.data,
            source_name=form.file.data.filename,
            source=pickle.dumps(df),
            result=pickle.dumps(scores),
            permutations=form.permutations.data,
        )
        experiment.network = network

        manager.session.add(experiment)
        manager.session.commit()

        return redirect(url_for('view_analysis_results', analysis_id=experiment.id))

    log.info('Added analysis service to %s', app)

    @app.route('/api/analysis/<analysis_id>')
    def get_analysis(analysis_id):
        """Returns data from analysis"""
        graph = get_graph_from_request(api)
        experiment = manager.session.query(Experiment).get(analysis_id)
        data = experiment.data

        results = {node: data[api.nid_node[node]] for node in graph.nodes_iter() if api.nid_node[node] in data}

        return jsonify(results)

    @app.route('/api/analysis/<analysis_id>/median')
    def get_analysis_median(analysis_id):
        """Returns data from analysis"""
        graph = get_graph_from_request(api)
        experiment = manager.session.query(Experiment).get(analysis_id)
        data = experiment.data

        results = {node: data[api.nid_node[node]][4] for node in graph.nodes_iter() if api.nid_node[node] in data}

        return jsonify(results)
