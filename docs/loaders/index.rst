.. _loaders:
.. rst-class:: section-icon-mdi-plus-box

**************
Importing Data
**************

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
   :demo: pause@1000,loaders:api-toggle
   :enable-only: loaders
   :demo-repeat: false

When API hints are enabled, you'll see Python code snippets showing how to access and
set various loader attributes. For example:

.. code-block:: python

    # When selecting a file loader, you might see:
    ldr = jdaviz.loaders['file']
    ldr.format = '1D Spectrum'  # Set the format
    ldr.filename = 'myfile.fits'  # Set the filename

The hints update as you interact with the UI, showing you the exact Python code
needed to reproduce your actions programmatically.

Differences from the Loaders API
================================

For most use cases, ``load()`` provides a simpler interface. Use the Loaders API when you need:

- More control over loading options
- Interactive configuration
- Data preview before loading
- Access to specialized loader features


Creating Jdaviz-readable Products
=================================

Spectroscopic data products (1D, 2D, and 3D) can be loaded
in the different ``jdaviz`` configurations using
essentially two methods, i.e., loading :class:`~specutils.Spectrum` objects or
from FITS files. Here, we list a few ways in which data can be packaged to be easily loaded
into a ``jdaviz`` configuration.

Data in a database
------------------

If the data are stored in a database, we recommend storing a :class:`~specutils.Spectrum` object
per entry. This would allow the user to query the data and visualize it in
``jdaviz`` with few lines of code; also see :ref:`create_product_spectrum1d_obj`.

Data in FITS files
------------------

If the data are stored as FITS files, we propose three options:

* :ref:`create_product_specutils_loader`
* :ref:`create_product_dedicated_loader`
* :ref:`create_product_spectrum1d_obj`

.. _create_product_specutils_loader:

Using an available specutils loader
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Available loaders can be listed with the following commands:

.. code-block:: python

    from specutils import Spectrum
    Spectrum.read.list_formats()

The majority are fairly specific to missions and instruments. Four formats
are more generic and adaptable: ``ASCII``, ``ECSV``, ``tabular-fits``, and
``wcs1d-fits``. More information on how to create files that are readable by
these loaders can be found on the `specutils GitHub repository
<https://github.com/astropy/specutils/tree/main/specutils/io/default_loaders>`_.

.. _create_product_dedicated_loader:

Creating a dedicated loader
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The `specutils documentation on how to create a custom loader
<https://specutils.readthedocs.io/en/stable/custom_loading.html#creating-a-custom-loader>`_
is available. We are working on the necessary documentation to prompt
``jdaviz`` to recognize a custom loader developed in ``specutils``.

.. _create_product_spectrum1d_obj:

Providing scripts to load the data as Spectrum objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If none of the above is an acceptable option, the user can create the data
products with their custom format and provide scripts or Jupyter Notebooks
that show how to read the products and create :class:`~specutils.Spectrum` objects
that can be read into ``jdaviz``.


Learn More
==========

- :ref:`loaders-sources` - Learn about different data sources
- :ref:`loaders-formats` - Learn about supported data formats
- :ref:`import-data` - See the full data import documentation
