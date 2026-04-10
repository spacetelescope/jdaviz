.. _userapi:
.. rst-class:: section-icon-mdi-code-tags

************************
API & Notebook Access
************************

Programmatic access to Jdaviz functionality for notebook workflows.

.. toctree::
   :maxdepth: 1

   cheatsheet
   api_hints
   show_options

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
