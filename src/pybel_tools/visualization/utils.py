import os

import jinja2

HERE = os.path.dirname(os.path.abspath(__file__))

TEMPLATE_ENVIRONMENT = jinja2.Environment(
    autoescape=False,
    loader=jinja2.FileSystemLoader(os.path.join(HERE, 'templates')),
    trim_blocks=False
)

TEMPLATE_ENVIRONMENT.globals['STATIC_PREFIX'] = HERE + '/static/'


def render_template(template_filename, context=None):
    if context is None:
        context = {}
    return TEMPLATE_ENVIRONMENT.get_template(template_filename).render(context)
