# -*- coding: utf-8 -*-

import csv
import logging
import pickle
import time
from operator import itemgetter

import flask
import pandas
import pybel
from flask import render_template, redirect, url_for, jsonify, make_response
from flask_login import login_required, current_user
from pybel.constants import GENE
from pybel.manager.models import Network
from six import StringIO

from .extension import get_manager, get_api
from .forms import DifferentialGeneExpressionForm
from .main_service import get_graph_from_request
from .models import Experiment
from .. import generation
from ..analysis import npa
from ..analysis.npa import RESULT_LABELS
from ..filters.node_deletion import remove_nodes_by_namespace
from ..integration import overlay_type_data
from ..mutation.collapse import rewire_variants_to_genes, collapse_by_central_dogma_to_genes

log = logging.getLogger(__name__)

LABEL = 'dgxa'


def build_analysis_service(app):
    """Builds the analysis service
    
    :param flask.Flask app: A Flask application
    """
    manager = get_manager(app)
    api = get_api(app)

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
        experiment_data = pickle.loads(experiment.result)
        return render_template(
            'analysis_results.html',
            experiment=experiment,
            columns=npa.RESULT_LABELS,
            data=sorted([(k, v) for k, v in experiment_data.items() if v[0]], key=itemgetter(1)),
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

        network = manager.get_network_by_id(network_id)
        graph = pybel.from_bytes(network.blob)

        remove_nodes_by_namespace(graph, {'MGI', 'RGD'})
        collapse_by_central_dogma_to_genes(graph)
        rewire_variants_to_genes(graph)

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
            user=current_user,
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
        data = pickle.loads(experiment.result)
        results = [{'node': node, 'data': data[api.nid_node[node]]} for node in graph.nodes_iter() if
                   api.nid_node[node] in data]

        return jsonify(results)

    @app.route('/api/analysis/<analysis_id>/median')
    def get_analysis_median(analysis_id):
        """Returns data from analysis"""
        graph = get_graph_from_request(api)
        experiment = manager.session.query(Experiment).get(analysis_id)
        data = pickle.loads(experiment.result)
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
        experiment_data = pickle.loads(experiment.result)
        csv_list.extend((ns, n) + tuple(v) for (_, ns, n), v in experiment_data.items())
        cw.writerows(csv_list)
        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = "attachment; filename=cmpa_{}.csv".format(analysis_id)
        output.headers["Content-type"] = "text/csv"
        return output

    log.info('Added analysis service to %s', app)
