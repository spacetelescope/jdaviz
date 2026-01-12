.. _userapi:

************************
API & Notebook Access
************************

Programmatic access to Jdaviz functionality for notebook workflows.

.. toctree::
   :maxdepth: 1

   cheatsheet
   api_hints
   show_options

Overview
========

Jdaviz provides comprehensive programmatic access for use in Jupyter notebooks:

**Cheatsheet**
  Quick reference guide for common API operations and workflows.

**API Hints**
  Interactive hints showing available parameters and options for loaders
  and plugins.

**Show Options**
  Configuration options for customizing how Jdaviz is displayed in notebooks.

Quick Examples
==============

.. code-block:: python

    import jdaviz

    # Create and show app
    jdaviz.show()

    # Load data
    jdaviz.load('mydata.fits', format='1D Spectrum')

    # Access a plugin
    plugin = jdaviz.plugins['Model Fitting']

    # Get data back
    spectrum = jdaviz.get_data('mydata')

See Also
========

- :doc:`../quickstart` - Getting started with Jdaviz
- :doc:`../plugin_api` - Plugin API documentation
- :doc:`../index_ref_api` - Full API reference
