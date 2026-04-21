"""
Sphinx extension that exposes the jdaviz wireframe demo assets.

Downstream packages (e.g. lcviz) can reuse the same wireframe HTML,
CSS, and actions JS by adding this extension to their Sphinx conf.py::

    extensions = [
        'jdaviz.ext.wireframe',
        'docs_wireframe_demo',
        # ...
    ]

Then embed a demo with project-specific steps in their template::

    <div data-wireframe-demo
         data-wireframe-config='{"htmlSrc": "jdaviz-wireframe.html", ...}'>
    </div>
"""

import os

_STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')


def setup(app):
    # Add the static directory so Sphinx copies HTML/CSS/JS into _static/
    app.connect('builder-inited', _add_static_path)

    # Register the CSS and JS so they are included on every page
    app.add_css_file('jdaviz-wireframe.css')
    app.add_js_file('jdaviz-wireframe-actions.js')

    return {
        'version': '0.1.0',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


def _add_static_path(app):
    app.config.html_static_path.append(_STATIC_DIR)
