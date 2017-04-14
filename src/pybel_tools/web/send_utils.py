# -*- coding: utf-8 -*-

from flask import send_file, Response, jsonify
from six import BytesIO, StringIO

from pybel import to_json_dict, to_cx_json, to_bel_lines, to_graphml, to_bytes, to_csv


def serve_network(graph, serve_format):
    """A helper function to serialize a graph and download as a file"""
    if serve_format is None or serve_format == 'json':
        data = to_json_dict(graph)
        return jsonify(data)

    if serve_format == 'cx':
        data = to_cx_json(graph)
        return jsonify(data)

    if serve_format == 'bytes':
        data = to_bytes(graph)
        return send_file(data, mimetype='application/octet-stream', as_attachment=True,
                         attachment_filename='graph.gpickle')

    if serve_format == 'bel':
        data = '\n'.join(to_bel_lines(graph))
        return Response(data, mimetype='text/plain')

    if serve_format == 'graphml':
        bio = BytesIO()
        to_graphml(graph, bio)
        bio.seek(0)
        data = StringIO(bio.read().decode('utf-8'))
        return send_file(data, mimetype='text/xml', attachment_filename='graph.graphml', as_attachment=True)

    if serve_format == 'csv':
        bio = BytesIO()
        to_csv(graph, bio)
        bio.seek(0)
        data = StringIO(bio.read().decode('utf-8'))
        return send_file(data, attachment_filename="graph.tsv", as_attachment=True)
