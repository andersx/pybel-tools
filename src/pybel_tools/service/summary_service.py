import logging

from flask import render_template

from pybel import from_bytes
from ..summary import count_functions, count_relations, count_error_types
from ..utils import prepare_c3
from ..web.utils import get_cache_manager

log = logging.getLogger(__name__)


def build_summary_service(app, manager=None):
    """Adds the endpoints for a synchronous web validation web app

    :param app: A Flask application
    :type app: Flask
    :param manager: A PyBEL cache manager
    :type manager: pybel.manager.cache.CacheManager
    """
    manager = get_cache_manager(app) if manager is None else manager

    @app.route('/summary/<int:graph_id>')
    def view_summary(graph_id):
        """Renders a page with the parsing errors for a given BEL script"""

        graph = manager.get_graph_by_id(graph_id)
        graph = from_bytes(graph.blob)

        return render_template(
            'summary.html',
            chart_1_data=prepare_c3(count_functions(graph), 'Entity Type'),
            chart_2_data=prepare_c3(count_relations(graph), 'Relationship Type'),
            chart_3_data=prepare_c3(count_error_types(graph), 'Error Type'),
            graph=graph,
            filename='{} (v{})'.format(graph.name, graph.version),
            time=None
        )

    log.info('Added summary endpoint to %s', app)
