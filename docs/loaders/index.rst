.. _loaders:
.. rst-class:: section-icon-mdi-plus-box

************
Data Loaders
************

Learn how to import data into Jdaviz from various sources and in different formats.

Overview
========

Jdaviz provides flexible data loading through a combination of **sources** and **formats**:

- **Sources** define *where* your data comes from (file, URL, Python object, etc.)
- **Formats** define *how* your data should be interpreted (1D spectrum, image, cube, etc.)

Using load()
============

The recommended way to load data is to use the :py:meth:`~jdaviz.core.helpers.ConfigHelper._load`
method on the configuration helper, whether that's the deconfigged mode as shown below, or a specific configuration such as ``Specviz``, ``Cubeviz``, etc. This provides a simple interface for loading data:

.. code-block:: python

    import jdaviz
    jdaviz.show()
    jdaviz.load('myspectrum.fits', format='1D Spectrum')

    # Alternatively
    from jdaviz import Specviz
    specviz = Specviz()
    specviz.show()
    specviz.load('myspectrum.fits')


Using Loaders API (Interactive)
===============================

For more control over the loading process, you can use the Loaders API. This provides an interactive way to:

- Select specific loaders
- Configure import options
- Inspect available options from dropdowns, etc.
- View API hints for available options
- Preview data before importing

The loaders are accessed through the ``loaders`` property on the helper:

.. code-block:: python

    # Access loaders
    loaders = jdaviz.loaders

    # Get list of available loaders
    print(loaders)

    # Use a specific loader
    ldr = loaders['object']  # Or file, file drop, or url

    # Configure loading options
    ldr.object = my_data  # or ldr.filename, ldr.url
    ldr.format = '1D Spectrum'

    # Import the data
    ldr.load()

The loaders interface provides access to parameters and options that control how the
data is loaded and processed.

Available Loaders
-----------------

.. toctree::
   :maxdepth: 2

   sources/index


Available formats
-----------------

.. toctree::
   :maxdepth: 2

   formats/index
   extensions


.. _loaders-api-hints:

Using API Hints
---------------

Jdaviz provides an API hints feature that helps you discover available attributes and
parameters for loaders. You can enable API hints:

.. code-block:: python

    jdaviz.toggle_api_hints()

Or in the UI, click the :guilabel:`API Hints` button in the top right.

.. wireframe-demo::
   :initial: loaders,loaders:select-tab=Data
   :demo: loaders:api-toggle
   :enable-only: loaders
   :demo-repeat: true

When API hints are enabled, you'll see Python code snippets showing how to access and
set various loader attributes. For example:

.. code-block:: python

    # When selecting a file loader, you might see:
    ldr = jdaviz.loaders['file']
    ldr.format = '1D Spectrum'  # Set the format
    ldr.filename = 'myfile.fits'  # Set the filename

The hints update as you interact with the UI, showing you the exact Python code
needed to reproduce your actions programmatically.

Differences from load_data()
============================

The ``load()`` method replaces the older ``load_data()`` method. Key differences:

1. Loader Auto-detection - ``load()`` attempts to auto-detect the appropriate loader based on the input

2. Format Selection - Provides more control over data format via the ``format`` parameter

3. Target Specification - Can direct data to specific viewers using ``target``

4. Consistent Interface - Works consistently across different data types

Differences from the Loaders API
================================

For most use cases, ``load()`` provides a simpler interface. Use the Loaders API when you need:

- More control over loading options
- Interactive configuration
- Data preview before loading
- Access to specialized loader features

While ``load_data()`` is still supported for backwards compatibility, ``load()`` is recommended for new code.


Learn More
==========

- :ref:`loaders-sources` - Learn about different data sources
- :ref:`loaders-formats` - Learn about supported data formats
- :ref:`import-data` - See the full data import documentation
