.. _info:
.. rst-class:: section-icon-mdi-information-outline

************************
Data Information Tools
************************

Access metadata, place markers, and view system logs.

.. toctree::
   :maxdepth: 1

   metadata
   markers
   logger

Overview
========

Jdaviz provides tools to inspect and interact with your data:

**Metadata Viewer**
  View FITS headers and other metadata associated with your loaded datasets.

**Interactive Markers**
  Place markers on images and spectra to mark points of interest and extract
  information at specific locations.

**Logger**
  View system messages, warnings, and errors from Jdaviz operations.

Accessing Information Tools
============================

These tools can be accessed through the plugin toolbar or programmatically:

.. code-block:: python

    # Access metadata
    metadata = app.plugins['Metadata']

    # View available information
    print(metadata)

See Also
========

- Individual information tool pages for detailed usage
