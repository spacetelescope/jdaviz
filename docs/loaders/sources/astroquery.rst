.. _loaders-source-astroquery:

.. rst-class:: section-icon-mdi-plus-box

:excl_platforms: mast


***************************
Loading from Astroquery
***************************

The Astroquery loader allows you to query and load data directly from astronomical archives.

.. note::
    This feature is currently in development. Stay tuned for updates!

Planned Usage
=============

Future support will include querying data from:

- MAST (Mikulski Archive for Space Telescopes)
- SDSS (Sloan Digital Sky Survey)
- Other archives supported by Astroquery

Check back for updates or `follow our GitHub repository <https://github.com/spacetelescope/jdaviz>`_
for announcements.

UI Access
=========

.. wireframe-demo:: _static/jdaviz-wireframe.html
   :js: jdaviz-wireframe-actions.js
   :css: jdaviz-wireframe.css
   :repeat: false
   :steps-json: [{"action": "show-sidebar", "value": "loaders", "delay": 1500, "caption": "Open the data loader"}, {"action": "select-dropdown", "value": "Source:astroquery", "delay": 1500, "caption": "Set source to astroquery"}]

API Access
==========

.. code-block:: python

    import jdaviz as jd
    jd.show()

    # Using loaders API
    ldr = jd.loaders['astroquery']
    ldr.show()

    ldr.source = 'M4'
    ...
    ldr.query_archive()


Since there are many options and the exposed options depend on previous selections, the best way to write a script to write a workflow loading from astroquery is to enable :ref:`userapi-api_hints`,
and interactively do a search in the UI and reproduce in a notebook cell:

.. wireframe-demo:: _static/jdaviz-wireframe.html
   :js: jdaviz-wireframe-actions.js
   :css: jdaviz-wireframe.css
   :repeat: false
   :steps-json: [{"action": "show-sidebar", "value": "loaders", "delay": 0}, {"action": "select-dropdown", "value": "Source:astroquery", "delay": 0}, {"action": "highlight", "target": "#source-select", "delay": 0}, {"action": "pause", "delay": 1000}, {"action": "api-toggle", "delay": 1500, "caption": "Toggle the API code hint"}]