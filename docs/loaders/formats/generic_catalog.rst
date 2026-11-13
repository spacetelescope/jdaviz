.. _loaders-format-generic_catalog:
.. rst-class:: section-icon-mdi-plus-box

:data-types: genericcatalog

.. _loaders-format-generic_catalog-overview:

***********************
Generic Catalog Format
***********************

Load astronomical catalogs for overlay and analysis. The Catalog format will be used for loading astronomical catalogs that can be
overlaid on images, added as a Table, and used for analysis. Generic catalogs can load any type of data.
    
Usage
=====

.. code-block:: python

    import jdaviz
    jdaviz.show()

    # Load a generic catalog
    jdaviz.load('catalog.ecsv', format='Generic Catalog') 

Data Requirements
=================

The Generic Catalog format imports any :class:`astropy.table.Table` or
:class:`~astropy.table.QTable` as a data collection entry. 


Supported File Formats
======================

The catalog should be in:

- FITS table
- ESCV 
- VOTable 


Catalog Parsing
===============

When loading via the UI, if a pair of RA/Dec or X/Y columns are parsable in the catalog, 
the format will default to :ref:`Source Catalog <loaders-format-catalog>`. Otherwise, it will default to Generic Catalog.

.. note::
    Sometimes multi-object spectral or image files can be auto-parsed as a catalog. 
    You can either change the format in the loader UI if the incorrect format is detected, or use the API to load the data using the correct format. 

Once the catalog is parsed, the ``Viewer`` must be selected.  The ``Viewer`` will default to load as a Generic Table,
but it can be loaded as a Scatter ``Viewer`` or Histogram ``Viewer``.  

UI Access
=========

.. guidestar-demo:: _static/jdaviz-wireframe.html
   :repeat: false
   :init-steps-json: [{"action":"disable-toolbar-except","value":"loaders"}]
   :steps-json: [{"action": "show-sidebar", "value": "loaders", "delay": 1500, "caption": "Open the data loader"}, {"action": "select-dropdown", "value": "Format:Catalog", "delay": 1000, "caption": "Set format to Catalog"}, {"action": "highlight", "target": "#format-select", "delay": 1500}]





See Also
========

- :ref:`loaders-format-catalog-overview` - For the source catalog functionality
