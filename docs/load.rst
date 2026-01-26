.. _import-data:

**************
Importing Data
**************

.. note::

    ``jdaviz`` is undergoing constant development. The latest enhancement is deconfigged mode
    where a user can load data into ``jdaviz`` - as shown below - and specify in what format the data
    should be parsed. Viewers are created based on the data loaded and user input.
    If you uncover any issues or bugs, you can
    `open a GitHub issue <https://github.com/spacetelescope/jdaviz/issues/new/choose>`_.

Jdaviz provides several ways to import data into the application. This guide will walk through the available methods and their use cases.

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

The main loaders available include:

- ``'file'`` - Load data from local files
- ``'url'`` - Load data from remote URLs/URIs
- ``'object'`` - Load Python objects directly (Spectrum1D, SpectrumList, NDData, etc)

Each loader has its own set of parameters that can be discovered through :ref:`api-hints`
or by accessing the loader object's attributes directly. For example, to see available formats for the object loader:

.. code-block:: python

    ldr.format.choices


Available formats
-----------------

- ``'1D Spectrum'`` - For individual 1D :class:`~specutils.Spectrum` objects or files containing a single spectrum
- ``'1D Spectrum List'`` - For `~specutils.SpectrumList` objects or files containing multiple spectra
- ``'1D Spectrum Concatenated'`` - For combining multiple spectra into a single spectrum
- ``'Image'`` - For 2D image data
- ``'2D Spectrum'`` - For 2D spectral data
- ``'3D Spectrum'`` - For 3D spectral cube data
- ``'Footprint'`` - For footprint overlays on images
- ``'Subset'`` - For loading subsets/regions
- ``'Trace'`` - For loading spectral traces

.. _api-hints:

Using API Hints
---------------

Jdaviz provides an API hints feature that helps you discover available attributes and
parameters for loaders. You can enable API hints:

.. code-block:: python

    jdaviz.toggle_api_hints()

Or in the UI, click the :guilabel:`API Hints` button in the top right.

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
