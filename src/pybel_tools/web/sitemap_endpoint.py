# -*- coding: utf-8 -*-
import logging
import sys

from flask import url_for, render_template
from flask_login import current_user

import pybel.utils
from ..utils import get_version

log = logging.getLogger(__name__)


def build_sitemap_endpoint(app, route=None):
    """Builds the sitemap endpoint"""

    @app.route("/sitemap" if route is None else route)
    def view_site_map():
        """Displays a page with the site map"""
        api_links = []
        page_links = []
        for rule in app.url_map.iter_rules():
            try:
                url = url_for(rule.endpoint)
                item = url, rule.endpoint
                if not current_user.admin and (url.startswith('/admin') or url.startswith('/api/admin')):
                    continue
                elif url.startswith('/api'):
                    api_links.append(item)
                else:
                    page_links.append((url, rule.endpoint))
            except:
                pass

        metadata = [
            ('Python Version', sys.version),
            ('PyBEL Version', pybel.utils.get_version()),
            ('PyBEL Tools Version', get_version()),
        ]
        return render_template("sitemap.html",
                               metadata=metadata,
                               links=sorted(set(page_links)),
                               api_links=sorted(set(api_links)))

    log.info('Added site map to %s', app)
