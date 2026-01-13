.. _userapi-cheatsheet:

**********
Cheatsheet
**********

Quick reference for common Jdaviz API operations and workflows in Jupyter notebooks.

Description
===========

This cheatsheet provides commonly used code snippets for working with Jdaviz programmatically
in Jupyter notebooks. It covers creating instances, loading data, accessing plugins, working
with viewers and subsets, and exporting data.

Common Workflows
================

Creating and Displaying
-----------------------

**Create and show inline:**

.. code-block:: python

    from jdaviz import Imviz

    imviz = Imviz()
    imviz.show()

**Customize display height:**

.. code-block:: python

    imviz.show(height=800)

**Show in sidecar (JupyterLab):**

.. code-block:: python

    imviz.show(loc='sidecar')

**Show in popout window:**

.. code-block:: python

    imviz.show(loc='popout')

**Using the top-level API:**

.. code-block:: python

    import jdaviz

    jdaviz.show()  # Auto-create instance
    jdaviz.load('mydata.fits', format='1D Spectrum')

Loading Data
------------

**Load from file:**

.. code-block:: python

    imviz.load('myimage.fits', format='Image')

**Load Python object:**

.. code-block:: python

    from astropy.nddata import NDData
    import numpy as np

    data = NDData(np.random.random((100, 100)))
    imviz.load(data, format='Image', data_label='Random Image')

**Load multiple files:**

.. code-block:: python

    imviz.load(['image1.fits', 'image2.fits'], format='Image')

**Using loaders for more control:**

.. code-block:: python

    ldr = imviz.loaders['file']
    ldr.filename = 'mydata.fits'
    ldr.format = 'Image'
    ldr.load()

Working with Plugins
--------------------

**Access a plugin:**

.. code-block:: python

    plot_opts = imviz.plugins['Plot Options']

**View plugin parameters:**

.. code-block:: python

    plot_opts  # Display in notebook shows available parameters

**Open plugin in tray:**

.. code-block:: python

    plot_opts.open_in_tray()

**Access all plugins:**

.. code-block:: python

    # List all available plugins
    print(imviz.plugins)

    # Iterate through plugins
    for name, plugin in imviz.plugins.items():
        print(f"{name}: {plugin}")

Working with Viewers
--------------------

**Access default viewer:**

.. code-block:: python

    viewer = imviz.default_viewer

**Access viewer by name:**

.. code-block:: python

    viewer = imviz.viewers['imviz-0']

**Create new viewer:**

.. code-block:: python

    viewer = imviz.new_viewers['imviz']()

**Modify viewer properties:**

.. code-block:: python

    # Set colormap
    viewer.set_colormap('Viridis')

    # Set stretch limits
    viewer.cuts = (0, 100)  # or '95%'

    # Set zoom level
    viewer.zoom_level = 2  # or 'fit'

    # Center on position
    viewer.center_on((512, 512))

**Destroy a viewer:**

.. code-block:: python

    imviz.destroy_viewer('viewer-name')

Working with Subsets
--------------------

**Create subset from region:**

.. code-block:: python

    from regions import CirclePixelRegion, PixCoord

    region = CirclePixelRegion(PixCoord(50, 50), 10)
    imviz.load(region, format='Subset', data_label='My Region')

**Get all subsets:**

.. code-block:: python

    subsets = imviz.plugins['Subset Tools'].get_regions()

**Access spectral regions:**

.. code-block:: python

    # For Specviz/Cubeviz
    regions = specviz.get_spectral_regions()

Exporting Data
--------------

**Export data from viewer:**

.. code-block:: python

    # Get data by label
    data = imviz.get_data('image_label')

    # For spectra
    spectrum = specviz.get_data('Spectrum 1')

    # With subset applied
    subset_spec = specviz.get_data(spectral_subset='Subset 1')

**Export all spectra:**

.. code-block:: python

    # Returns dict of all loaded spectra
    all_spectra = specviz.get_spectra()

**Export plugin results:**

.. code-block:: python

    # Model fitting results
    models = specviz.fitted_models

    # Or use plugin API
    model_fitting = specviz.plugins['Model Fitting']
    model = model_fitting.get_models()

**Write to file:**

.. code-block:: python

    # Get data and write
    spectrum = specviz.get_data('Spectrum 1')
    spectrum.write('output.fits')

API Hints
---------

**Enable API hints:**

.. code-block:: python

    imviz.toggle_api_hints()  # Toggle on/off
    imviz.toggle_api_hints(enabled=True)  # Explicitly enable

When enabled, API hints show you the equivalent Python code for UI interactions, making it easy
to automate your workflows.

Configuration-Specific Examples
================================

Imviz
-----

.. code-block:: python

    from jdaviz import Imviz

    imviz = Imviz()
    imviz.show()
    imviz.load('hst_image.fits', format='Image')

    viewer = imviz.default_viewer
    viewer.set_colormap('Viridis')
    viewer.zoom_level = 'fit'

Specviz
-------

.. code-block:: python

    from jdaviz import Specviz

    specviz = Specviz()
    specviz.show()
    specviz.load('spectrum.fits', format='1D Spectrum')

    # Fit a line
    model_fitting = specviz.plugins['Model Fitting']
    model_fitting.open_in_tray()

Cubeviz
-------

.. code-block:: python

    from jdaviz import Cubeviz

    cubeviz = Cubeviz()
    cubeviz.show()
    cubeviz.load('datacube.fits', format='3D Spectrum')

    # Extract spectrum from subset
    spectral_extraction = cubeviz.plugins['Spectral Extraction']
    spectral_extraction.aperture = 'Subset 1'
    spectrum = spectral_extraction.extract()

Specviz2d
---------

.. code-block:: python

    from jdaviz import Specviz2d

    specviz2d = Specviz2d()
    specviz2d.show()
    specviz2d.load('2d_spectrum.fits', format='2D Spectrum')

Mosviz
------

.. code-block:: python

    from jdaviz import Mosviz

    mosviz = Mosviz()
    mosviz.show()
    # Load MOS data
    mosviz.load(directory='path/to/mos/data/')

Rampviz
-------

.. code-block:: python

    from jdaviz import Rampviz

    rampviz = Rampviz()
    rampviz.show()
    rampviz.load('ramp_data.fits')

See Also
========

* :doc:`../quickstart` - Getting started with Jdaviz
* :doc:`../plugin_api` - Plugin API documentation
* :doc:`api_hints` - Using API hints for discovery
* :doc:`show_options` - Customizing display options
* :doc:`../sample_notebooks` - Example notebooks
