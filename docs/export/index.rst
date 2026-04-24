.. _export:
.. rst-class:: section-icon-mdi-content-save

***************
Exporting Data
***************

Jdaviz allows you to export various data products created during your analysis:

.. toctree::
   :maxdepth: 1

   viewers
   datasets
   subsets
   plugin_tables
   plugin_plots


UI Access
=========

.. wireframe-demo:: _static/jdaviz-wireframe.html
   :repeat: false
   :init-steps-json: [{"action":"disable-toolbar-except","value":"save"}]
   :steps-json: [{"action": "show-sidebar", "value": "save", "delay": 1500, "caption": "Open the export sidebar"}]

API Access
==========

.. code-block:: python

   plg = jdaviz.plugins['Export']
   plg.dataset = 'my-dataset'
   plg.dataset_format = 'FITS'
   plg.export()

Since there are many options and the exposed options depend on previous selections, the best way to explore API options is to enable :ref:`userapi-api_hints`:

.. wireframe-demo:: _static/jdaviz-wireframe.html
   :repeat: true
   :init-steps-json: [{"action":"disable-toolbar-except","value":"save"}]
   :steps-json: [{"action": "show-sidebar", "value": "save", "delay": 0}, {"action": "pause", "delay": 1000}, {"action": "api-toggle", "delay": 1500, "caption": "Toggle the API code hint"}]