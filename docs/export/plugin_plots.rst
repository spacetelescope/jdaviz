.. _export-plugin_plots:
.. rst-class:: section-icon-mdi-content-save

************
Plugin Plots
************


Several plugins produce plots that can be exported:

- back into your Jupyter notebook
- as a file

Supported Formats
=================

Plots can be exported as:

- PNG 

.. note::
   The image size will be the exact size and state of the plugin plot (i.e. as if you took a screenshot of the plot).  
   Confirm the plot height and width before exporting.  


API Access
==========

.. code-block:: python

   plg = jd.plugins['Export']
   plg.plugin_plot = 'Plugin Name: plot'
   plg.filename = 'my-subset'
   plg.export()


UI Access
=========

.. guidestar-demo:: _static/jdaviz-wireframe.html
   :repeat: false
   :init-steps-json: [{"action":"disable-toolbar-except","value":"save"}]
   :steps-json: [{"action": "show-sidebar", "value": "save", "delay": 1500, "caption": "Open the export sidebar"}]
