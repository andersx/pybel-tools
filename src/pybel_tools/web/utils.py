# -*- coding: utf-8 -*-

import itertools as itt
import logging
from collections import Counter

import flask
import networkx as nx
from flask import render_template, jsonify, Flask
from flask_bootstrap import Bootstrap
from flask_login import current_user
from sqlalchemy.exc import IntegrityError

from pybel.canonicalize import decanonicalize_node
from .constants import integrity_message
from ..analysis.stability import *
from ..constants import CNAME
from ..summary import get_contradiction_summary, count_functions, count_relations, count_error_types, get_translocated, \
    get_degradations, get_activities, count_namespaces, group_errors
from ..summary.edge_summary import count_diseases, get_unused_annotations, get_unused_list_annotation_values
from ..summary.error_summary import get_undefined_namespaces, get_undefined_annotations, \
    get_namespaces_with_incorrect_names
from ..summary.export import info_list
from ..summary.node_properties import count_variants
from ..summary.node_summary import get_unused_namespaces
from ..utils import prepare_c3, count_dict_values

log = logging.getLogger(__name__)


def render_upload_error(exc):
    """Builds a flask Response for an exception.
    
    :type exc: Exception
    """
    return render_template('parse_error.html', error_title='Upload Error', error_text=str(exc))


def try_insert_graph(manager, graph, api=None):
    """Inserts a graph and sends an okay message if success. else renders upload page
    
    :type manager: pybel.manager.cache.CacheManager
    :param pybel.BELGraph graph: A BEL graph
    :return: The HTTP response to use as a Flask response
    """
    try:
        network = manager.insert_graph(graph)

        if api:
            api.add_network(network.id, graph)

        return jsonify({
            'status': 200,
            'network_id': network.id
        })
    except IntegrityError as e:
        flask.flash(integrity_message.format(graph.name, graph.version))
        log.exception('Integrity error')
        manager.rollback()
        return render_upload_error(e)
    except Exception as e:
        flask.flash("Error storing in database")
        log.exception('Upload error')
        return render_upload_error(e)


def get_app():
    """Builds a Flask app for the PyBEL web service
    
    :rtype: flask.Flask
    """
    app = Flask(__name__)
    log.debug('made app %s', app)
    Bootstrap(app)
    log.debug('added bootstrap to app %s', app)
    return app


def sanitize_list_of_str(l):
    """Strips all strings in a list and filters to the non-empty ones
    
    :type l: iter[str]
    :rtype: list[str]
    """
    return [e for e in (e.strip() for e in l) if e]


def render_graph_summary_no_api(graph):
    """Renders the graph summary page if not saving the graph
    
    :param pybel.BELGraph graph: A BEL graph
    :return: A Flask Resposne object
    """
    hub_data = {graph.node[node][CNAME]: count for node, count in Counter(graph.degree()).most_common(25)}
    centrality_data = {graph.node[node][CNAME]: count for node, count in
                       calc_betweenness_centality(graph).most_common(25)}
    disease_data = {graph.node[node][CNAME]: count for node, count in count_diseases(graph).most_common(25)}

    undefined_namespaces = get_undefined_namespaces(graph)
    undefined_annotations = get_undefined_annotations(graph)
    namespaces_with_incorrect_names = get_namespaces_with_incorrect_names(graph)

    unused_namespaces = get_unused_namespaces(graph)
    unused_annotations = get_unused_annotations(graph)
    unused_list_annotation_values = get_unused_list_annotation_values(graph)

    return render_template(
        'summary.html',
        chart_1_data=prepare_c3(count_functions(graph), 'Entity Type'),
        chart_2_data=prepare_c3(count_relations(graph), 'Relationship Type'),
        chart_3_data=prepare_c3(count_error_types(graph), 'Error Type'),
        chart_4_data=prepare_c3({
            'Translocations': len(get_translocated(graph)),
            'Degradations': len(get_degradations(graph)),
            'Molecular Activities': len(get_activities(graph))
        }, 'Modifier Type'),
        chart_5_data=prepare_c3(count_variants(graph), 'Node Variants'),
        chart_6_data=prepare_c3(count_namespaces(graph), 'Namespaces'),
        chart_7_data=prepare_c3(hub_data, 'Top Hubs'),
        chart_8_data=prepare_c3(centrality_data, 'Top Central'),
        chart_9_data=prepare_c3(disease_data, 'Pathologies'),
        error_groups=count_dict_values(group_errors(graph)).most_common(20),
        info_list=info_list(graph),
        graph=graph,
        time=None,
        undefined_namespaces=sorted(undefined_namespaces),
        unused_namespaces=sorted(unused_namespaces),
        undefined_annotations=sorted(undefined_annotations),
        unused_annotations=sorted(unused_annotations),
        unused_list_annotation_values=sorted(unused_list_annotation_values.items()),
        current_user=current_user,
        namespaces_with_incorrect_names=namespaces_with_incorrect_names
    )


def render_graph_summary(graph_id, graph, api=None):
    """Renders the graph summary page
    
    :param int graph_id: 
    :param pybel.BELGraph graph: 
    :param DictionaryService api: 
    :return: 
    """
    if api is None:
        return render_graph_summary_no_api(graph)

    hub_data = api.get_top_degree(graph_id)
    centrality_data = api.get_top_centrality(graph_id)
    disease_data = api.get_top_comorbidities(graph_id)

    def dcn(node):
        return decanonicalize_node(graph, node)

    unstable_pairs = itt.chain.from_iterable([
        ((u, v, 'Chaotic') for u, v, in get_chaotic_pairs(graph)),
        ((u, v, 'Dampened') for u, v, in get_dampened_pairs(graph)),
    ])
    unstable_pairs = [(dcn(u), api.get_node_id(u), dcn(v), api.get_node_id(v), label) for u, v, label in unstable_pairs]

    contradictory_pairs = [(dcn(u), api.get_node_id(u), dcn(v), api.get_node_id(v), relation) for u, v, relation in
                           get_contradiction_summary(graph)]

    contradictory_triplets = itt.chain.from_iterable([
        ((a, b, c, 'Separate') for a, b, c in get_separate_unstable_correlation_triples(graph)),
        ((a, b, c, 'Mutual') for a, b, c in get_mutually_unstable_correlation_triples(graph)),
        ((a, b, c, 'Jens') for a, b, c in get_jens_unstable_alpha(graph)),
        ((a, b, c, 'Increase Mismatch') for a, b, c in get_increase_mismatch_triplets(graph)),
        ((a, b, c, 'Decrease Mismatch') for a, b, c in get_decrease_mismatch_triplets(graph)),

    ])

    contradictory_triplets = [(dcn(a), api.get_node_id(a), dcn(b), api.get_node_id(b), dcn(c), api.get_node_id(c), d)
                              for a, b, c, d in contradictory_triplets]

    unstable_triplets = itt.chain.from_iterable([
        ((a, b, c, 'Chaotic') for a, b, c in get_chaotic_triplets(graph)),
        ((a, b, c, 'Dampened') for a, b, c in get_dampened_triplets(graph)),
    ])
    unstable_triplets = [(dcn(a), api.get_node_id(a), dcn(b), api.get_node_id(b), dcn(c), api.get_node_id(c), d) for
                         a, b, c, d in unstable_triplets]

    undefined_namespaces = get_undefined_namespaces(graph)
    undefined_annotations = get_undefined_annotations(graph)
    namespaces_with_incorrect_names = get_namespaces_with_incorrect_names(graph)

    unused_namespaces = get_unused_namespaces(graph)
    unused_annotations = get_unused_annotations(graph)
    unused_list_annotation_values = get_unused_list_annotation_values(graph)

    return render_template(
        'summary.html',
        chart_1_data=prepare_c3(count_functions(graph), 'Entity Type'),
        chart_2_data=prepare_c3(count_relations(graph), 'Relationship Type'),
        chart_3_data=prepare_c3(count_error_types(graph), 'Error Type'),
        chart_4_data=prepare_c3({
            'Translocations': len(get_translocated(graph)),
            'Degradations': len(get_degradations(graph)),
            'Molecular Activities': len(get_activities(graph))
        }, 'Modifier Type'),
        chart_5_data=prepare_c3(count_variants(graph), 'Node Variants'),
        chart_6_data=prepare_c3(count_namespaces(graph), 'Namespaces'),
        chart_7_data=prepare_c3(hub_data, 'Top Hubs'),
        chart_8_data=prepare_c3(centrality_data, 'Top Central'),
        chart_9_data=prepare_c3(disease_data, 'Pathologies'),
        error_groups=count_dict_values(group_errors(graph)).most_common(20),
        info_list=info_list(graph),
        contradictions=contradictory_pairs,
        unstable_pairs=unstable_pairs,
        contradictory_triplets=contradictory_triplets,
        unstable_triplets=unstable_triplets,
        graph=graph,
        graph_id=graph_id,
        time=None,
        undefined_namespaces=sorted(undefined_namespaces),
        unused_namespaces=sorted(unused_namespaces),
        undefined_annotations=sorted(undefined_annotations),
        unused_annotations=sorted(unused_annotations),
        unused_list_annotation_values=sorted(unused_list_annotation_values.items()),
        current_user=current_user,
        namespaces_with_incorrect_names=namespaces_with_incorrect_names
    )


def calc_betweenness_centality(graph):
    try:
        res = Counter(nx.betweenness_centrality(graph, k=200))
        return res
    except:
        return Counter(nx.betweenness_centrality(graph))
