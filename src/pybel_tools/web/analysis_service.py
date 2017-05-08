# -*- coding: utf-8 -*-

import csv
import datetime
import logging
import pickle
import time
from operator import itemgetter

import flask
import pandas
from flask import render_template, redirect, url_for, jsonify, make_response
from flask_login import login_required, current_user
from six import StringIO
from sqlalchemy import Column, Integer, DateTime, Binary, Text, ForeignKey, String
from sqlalchemy.orm import relationship

import pybel
from pybel.constants import GENE
from pybel.manager.models import Base, Network, NETWORK_TABLE_NAME
from .dict_service import get_graph_from_request
from .forms import DifferentialGeneExpressionForm
from .. import generation
from ..analysis import npa
from ..analysis.npa import RESULT_LABELS
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

    user_id = Column(Integer)
    username = Column(String(255))

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
    @app.route('/analysis/<network_id>')
    def view_analyses(network_id=None):
        """Views a list of all analyses, with optional filter by network id"""
        experiment_query = manager.session.query(Experiment)

        if network_id is not None:
            experiment_query = experiment_query.filter(Experiment.network_id == network_id)

        experiments = experiment_query.all()
        return render_template('analysis_list.html', experiments=experiments, current_user=current_user)

    @app.route('/analysis/results/<int:analysis_id>')
    def view_analysis_results(analysis_id):
        """View the results of a given analysis"""
        experiment = manager.session.query(Experiment).get(analysis_id)
        return render_template(
            'analysis_results.html',
            experiment=experiment,
            columns=npa.RESULT_LABELS,
            data=sorted([(k, v) for k, v in experiment.data.items() if v[0]], key=itemgetter(1)),
            current_user=current_user
        )

    @app.route('/analysis/results/<int:analysis_id>/drop')
    @login_required
    def delete_analysis_results(analysis_id):
        """Drops an analysis"""
        if not current_user.admin:
            flask.abort(403)

        manager.session.query(Experiment).get(analysis_id).delete()
        manager.session.commit()
        flask.flash('Dropped Experiment #{}'.format(analysis_id))
        return redirect(url_for('view_analyses'))

    @app.route('/analysis/upload/<int:network_id>', methods=('GET', 'POST'))
    @login_required
    def view_analysis_uploader(network_id):
        """Views the results of analysis on a given graph"""
        form = DifferentialGeneExpressionForm()

        if not form.validate_on_submit():
            name, = manager.session.query(Network.name).filter(Network.id == network_id).one()
            return render_template('analyze_dgx.html', form=form, network_name=name)

        log.info('analyzing %s: %s with CMPA (%d trials)', form.file.data.filename, form.description.data,
                 form.permutations.data)

        t = time.time()

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

        log.info('done running CMPA in %.2fs', time.time() - t)

        experiment = Experiment(
            description=form.description.data,
            source_name=form.file.data.filename,
            source=pickle.dumps(df),
            result=pickle.dumps(scores),
            permutations=form.permutations.data,
            user_id=current_user.github_id,
            username=current_user.username,
        )
        experiment.network = network

        manager.session.add(experiment)
        manager.session.commit()

        return redirect(url_for('view_analysis_results', analysis_id=experiment.id))

    @app.route('/api/analysis/<analysis_id>')
    def get_analysis(analysis_id):
        """Returns data from analysis"""
        graph = get_graph_from_request(api)
        experiment = manager.session.query(Experiment).get(analysis_id)
        data = experiment.data

        results = [{'node': node, 'data': data[api.nid_node[node]]} for node in graph.nodes_iter() if
                   api.nid_node[node] in data]

        return jsonify(results)

    @app.route('/api/analysis/<analysis_id>/median')
    def get_analysis_median(analysis_id):
        """Returns data from analysis"""
        graph = get_graph_from_request(api)
        experiment = manager.session.query(Experiment).get(analysis_id)
        data = experiment.data
        # position 3 is the 'median' score
        results = {node: data[api.nid_node[node]][3] for node in graph.nodes_iter() if api.nid_node[node] in data}

        return jsonify(results)

    @app.route('/api/analysis/<analysis_id>/download')
    def download_analysis(analysis_id):
        """Downloads data from a given experiment as a CSV"""
        experiment = manager.session.query(Experiment).get(analysis_id)
        si = StringIO()
        cw = csv.writer(si)
        csv_list = [('Namespace', 'Name') + tuple(RESULT_LABELS)]
        csv_list.extend((ns, n) + tuple(v) for (_, ns, n), v in experiment.data.items())
        cw.writerows(csv_list)
        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = "attachment; filename=cmpa_{}.csv".format(analysis_id)
        output.headers["Content-type"] = "text/csv"
        return output

    log.info('Added analysis service to %s', app)
