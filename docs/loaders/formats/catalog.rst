.. _loaders-format-catalog:
.. rst-class:: section-icon-mdi-plus-box

:data-types: catalog

*********************
Catalog Format
*********************

Load astronomical catalogs for overlay and analysis.

.. .. note::
..     This feature is currently in development. Stay tuned for updates!

Overview
========

The Catalog format will be used for loading astronomical catalogs that can be
overlaid on images, added as a Table, and used for analysis.

There are two types of catalogs that can be loaded:

    - **Source Catalog** (formally Catalog) - catalog where each row likely represents an object on the sky.  Must contain object coordinates. 
    - **Generic Catalog** - catalog with any type of data
    
Usage
=====

.. code-block:: python

    import jdaviz
    jdaviz.show()

    # Load a source catalog
    jdaviz.load('source_catalog.ecsv', format='Source Catalog') 

    # Load a generic catalog
    jdaviz.load('catalog.ecsv', format='Generic Catalog') 

Data Requirements
=================

The **Source Catalog** or **Generic Catalog** format imports any :class:`astropy.table.Table` or
:class:`~astropy.table.QTable` as a data collection. 

**Source Catalog** requires the following columns:

    - Right Ascention (RA) and/or X pixel
    - Declination (Dec) and/or Y pixel


Supported File Formats
======================

The catalog should be in:

    - FITS table
    - ESCV 
    - VOTable 


Catalog Parsing
===============

If loaded through the UI, if RA and Dec, or X and Y columns are parsable in the catalog, 
the format will default to **Source Catalog**. Otherwise, it will default to **Generic Catalog**.

.. note::
    Sometimes multi-object spectral or image files can be auto-parsed as a catalog. 
    Either change format if the correct format is detected, or use the API to load the data in using the correct format. 

Once the catalog is parsed, the `Viewer`` must be selected.  The `Viewer`` will default to load as a **Source Catalog Table** or **Generic Table**,
but it can be loaded as a **Scatter** `Viewer` or **Histogram** `Viewer`.  If it is a **Source Catalog**, 
the catalog can be loaded onto an **Image** `Viewer`` as markers (if a prior image has been loaded). 

UI Access
=========

.. guidestar-demo:: _static/jdaviz-wireframe.html
   :repeat: false
   :init-steps-json: [{"action":"disable-toolbar-except","value":"loaders"}]
   :steps-json: [{"action": "show-sidebar", "value": "loaders", "delay": 1500, "caption": "Open the data loader"}, {"action": "select-dropdown", "value": "Format:Catalog", "delay": 1000, "caption": "Set format to Catalog"}, {"action": "highlight", "target": "#format-select", "delay": 1500}]




.. See Also
.. ========

.. - :doc:`../../imviz/plugins` - For the current catalog search functionality
