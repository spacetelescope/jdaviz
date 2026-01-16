.. _loaders-format-catalog:

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

.. wireframe-demo::
   :demo: loaders,loaders@1000:select-dropdown=Format:Catalog,loaders:highlight=#format-select
   :enable-only: loaders
   :demo-repeat: false

See Also
========

- :doc:`../../imviz/plugins` - For the current catalog search functionality
