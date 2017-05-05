# -*- coding: utf-8 -*-

import itertools as itt
import logging
import traceback
from collections import Counter

import flask
import networkx as nx
from flask import render_template, jsonify, Flask
from flask_bootstrap import Bootstrap
from sqlalchemy.exc import IntegrityError

from pybel.canonicalize import decanonicalize_node
from ..analysis import get_chaotic_pairs, get_dampened_pairs, get_separate_unstable_correlation_triples, \
    get_mutually_unstable_correlation_triples
from ..constants import CNAME
from ..summary import get_contradiction_summary, count_functions, count_relations, count_error_types, get_translocated, \
    get_degradations, get_activities, count_namespaces, group_errors
from ..summary.edge_summary import count_diseases, get_unused_annotations, get_unused_list_annotation_values
from ..summary.error_summary import get_undefined_namespaces, get_undefined_annotations
from ..summary.export import info_list
from ..summary.node_properties import count_variants
from ..summary.node_summary import get_unused_namespaces
from ..utils import prepare_c3, count_dict_values

log = logging.getLogger(__name__)


def render_upload_error(exc):
    """Builds a flask Response for an exception.
    
    :type exc: Exception
    """
    traceback_lines = traceback.format_exc().split('\n')
    return render_template(
        'parse_error.html',
        error_title='Upload Error',
        error_text=str(exc),
        traceback_lines=traceback_lines
    )


def try_insert_graph(manager, graph, api=None):
    """Inserts a graph and sends an okay message if success. else renders upload page
    
    :param manager: 
    :type manager: pybel.manager.cache.CacheManager
    :param graph: 
    :type graph: pybel.BELGraph
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
        flask.flash("Graph with same Name/Version already exists. Try bumping the version number.")
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
    
    :type l: list[str]
    :rtype: list[str]
    """
    return [e for e in (e.strip() for e in l) if e]


def render_graph_summary(graph_id, graph, api=None):
    """Renders the graph summary page
    
    :param int graph_id: 
    :param pybel.BELGraph graph: 
    :param DictionaryService api: 
    :return: 
    """
    if api is not None:
        hub_data = api.get_top_degree(graph_id)
        centrality_data = api.get_top_centrality(graph_id)
        disease_data = api.get_top_comorbidities(graph_id)
    else:
        hub_data = {graph.node[node][CNAME]: count for node, count in Counter(graph.degree()).most_common(25)}
        centrality_data = {graph.node[node][CNAME]: count for node, count in
                           calc_betweenness_centality(graph).most_common(25)}
        disease_data = {graph.node[node][CNAME]: count for node, count in count_diseases(graph).most_common(25)}

    unstable_pairs = list(itt.chain.from_iterable([
        ((decanonicalize_node(graph, u), decanonicalize_node(graph, v), 'Chaotic') for u, v, in
         get_chaotic_pairs(graph)),
        ((decanonicalize_node(graph, u), decanonicalize_node(graph, v), 'Dampened') for u, v, in
         get_dampened_pairs(graph)),
    ]))

    contradictory_pairs = list((decanonicalize_node(graph, u), decanonicalize_node(graph, v), relation) for
                               u, v, relation in get_contradiction_summary(graph))

    separate_unstable_triples = list(tuple(decanonicalize_node(graph, node) for node in nodes) for nodes in
                                     get_separate_unstable_correlation_triples(graph))
    mutually_unstable_triples = list(tuple(decanonicalize_node(graph, node) for node in nodes) for nodes in
                                     get_mutually_unstable_correlation_triples(graph))

    unstable_correlation_triplets = list(itt.chain.from_iterable([
        ((a, b, c, 'Seperate') for a, b, c in separate_unstable_triples),
        ((a, b, c, 'Mutual') for a, b, c in mutually_unstable_triples),
    ]))

    undefined_namespaces = get_undefined_namespaces(graph)
    undefined_annotations = get_undefined_annotations(graph)

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
        unstable_correlation_triplets=unstable_correlation_triplets,
        graph=graph,
        graph_id=graph_id,
        time=None,
        undefined_namespaces=sorted(undefined_namespaces),
        unused_namespaces=sorted(unused_namespaces),
        undefined_annotations=sorted(undefined_annotations),
        unused_annotations=sorted(unused_annotations),
        unused_list_annotation_values=sorted(unused_list_annotation_values.items()),
    )


def canonicalize_node_keys(d, graph):
    return {graph.node[node][CNAME] for node, value in d.items()}


def calc_betweenness_centality(graph):
    try:
        res = Counter(nx.betweenness_centrality(graph, k=200))
        return res
    except:
        return Counter(nx.betweenness_centrality(graph))
