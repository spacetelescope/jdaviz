.. _loaders:
.. rst-class:: section-icon-mdi-plus-box

************
Data Loaders
************

Learn how to import data into Jdaviz from various sources and in different formats.

.. toctree::
   :maxdepth: 2

   sources/index
   formats/index
   extensions

Overview
========

Jdaviz provides flexible data loading through a combination of **sources** and **formats**:

- **Sources** define *where* your data comes from (file, URL, Python object, etc.)
- **Formats** define *how* your data should be interpreted (1D spectrum, image, cube, etc.)

Quick Start
===========

The simplest way to load data is using the ``load()`` method:

.. code-block:: python

    import jdaviz
    jdaviz.show()
    jdaviz.load('mydata.fits', format='1D Spectrum')

For more control, use the loaders API:

.. code-block:: python

    # Access a specific loader
    ldr = jdaviz.loaders['file']
    ldr.filename = 'mydata.fits'
    ldr.format = '1D Spectrum'
    ldr.load()

Learn More
==========

- :ref:`loaders-sources` - Learn about different data sources
- :ref:`loaders-formats` - Learn about supported data formats
- :ref:`import-data` - See the full data import documentation
