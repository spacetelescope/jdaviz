.. _loaders-format-catalog:
.. rst-class:: section-icon-mdi-plus-box

:data-types: catalog

*********************
Catalog Format
*********************

Load astronomical catalogs for overlay and analysis.

.. note::
    This feature is currently in development. Stay tuned for updates!

Overview
========

The Catalog format will be used for loading astronomical source catalogs that can be
overlaid on images and used for analysis.

Planned Features
================

Future support will include:

- Loading catalogs from files (FITS tables, ECSV, VOTable)
- Overlaying catalog sources on images
- Selecting sources for analysis
- Cross-matching with loaded data

UI Access
=========

.. wireframe-demo:: _static/jdaviz-wireframe.html
   :repeat: false
   :init-steps-json: [{"action":"disable-toolbar-except","value":"loaders"}]
   :steps-json: [{"action": "show-sidebar", "value": "loaders", "delay": 1500, "caption": "Open the data loader"}, {"action": "select-dropdown", "value": "Format:Catalog", "delay": 1000, "caption": "Set format to Catalog"}, {"action": "highlight", "target": "#format-select", "delay": 1500}]

See Also
========

- :doc:`../../imviz/plugins` - For the current catalog search functionality
