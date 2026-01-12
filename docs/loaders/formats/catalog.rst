.. _loaders-format-catalog:

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

Temporary Workaround
====================

Currently, you can load catalogs using the Catalog Search plugin in Imviz:

.. code-block:: python

    from jdaviz import Imviz
    imviz = Imviz()
    imviz.show()
    imviz.load('image.fits', format='Image')

    # Use the Catalog Search plugin from the toolbar

See Also
========

- :doc:`../../imviz/plugins` - For the current catalog search functionality
