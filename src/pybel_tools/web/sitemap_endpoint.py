# -*- coding: utf-8 -*-
import logging

from flask import url_for, render_template

import pybel.utils
from ..utils import get_version
import sys
log = logging.getLogger(__name__)


def build_sitemap_endpoint(app, route=None):
    @app.route("/" if route is None else route)
    def view_site_map():
        api_links = []
        page_links = []
        for rule in app.url_map.iter_rules():
            try:
                url = url_for(rule.endpoint)
                item = url, rule.endpoint
                if url.startswith('/admin') or url.startswith('/api/admin'):
                    continue
                elif url.startswith('/api'):
                    api_links.append(item)
                else:
                    page_links.append((url, rule.endpoint))
            except:
                pass

        metadata = [
            ('Python', sys.version),
            ('PyBEL Version', pybel.utils.get_version()),
            ('PyBEL Tools Version', get_version()),
        ]
        return render_template("sitemap.html",
                               metadata=metadata,
                               links=sorted(set(page_links)),
                               api_links=sorted(set(api_links)))

    log.info('Added site map to %s', app)
