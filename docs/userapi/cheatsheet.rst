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

    import jdaviz as jd

    jd.show()

**Create new app:**

.. code-block:: python

    import jdaviz as jd

    jd2 = jd.new_app()

**Customize display height:**

.. code-block:: python

    jd.show(height=800)

**Show in sidecar (JupyterLab):**

.. code-block:: python

    jd.show(loc='sidecar')

**Show in popout window:**

.. code-block:: python

    jd.show(loc='popout')

**Using the top-level API:**

.. code-block:: python

    import jdaviz as jd

    jd.load('mydata.fits', format='1D Spectrum')

Loading Data
------------

**Load from file:**

.. code-block:: python

    jd.load('myimage.fits', format='Image')


**Load from MAST URI:**

.. code-block:: python

    jd.load('mast:JWST/product/myfile_x1d.fits', format='1D Spectrum')

**Load Python object:**

.. code-block:: python

    from astropy.nddata import NDData
    import numpy as np

    data = NDData(np.random.random((100, 100)))
    jd.load(data, format='Image', data_label='Random Image')

**Using loaders for more control:**

.. code-block:: python

    ldr = jd.loaders['file']
    ldr.filename = 'mydata.fits'
    ldr.format = 'Image'
    ldr.load()

**Using loaders for astroquery with Gaia:**

.. code-block:: python

    ldr = jd.loaders['astroquery']
    ldr.search_input = 'Source'
    ldr.viewer = 'Image' 
    ldr.source = '259, 43' # RA_degree, Dec_degree
    ldr.telescope='Gaia'
    ldr.max_results = 10
    ldr.query_archive()

    ldr.target='Source Catalog Table'
    ldr.format='Source Catalog'

    ldr.importer.col_ra = 'ra'
    ldr.importer.col_dec = 'dec'
    ldr.importer.coord_frame = 'icrs'
    ldr.importer.col_other = ['source_id', 'parallax']
    ldr.importer.col_id = 'Default (index)'
    ldr.importer.data_label = 'Source Catalog'
    ldr.importer.viewer.create_new = 'Source Catalog Table'
    ldr.importer.viewer.new_label = 'Source Catalog Table'
    ldr.load()

Working with Plugins
--------------------

**Access a plugin:**

.. code-block:: python

    plg = jd.plugins['Plot Options']

**View plugin parameters:**

.. code-block:: python

    dir(plg)  # Display in notebook shows available parameters

**Open plugin in tray:**

.. code-block:: python

    plg.open_in_tray()

**Access all plugins:**

.. code-block:: python

    # List all available plugins
    print(jd.plugins)

    # Iterate through plugins
    for name, plugin in jd.plugins.items():
        print(f"{name}: {plugin}")

Working with Viewers
--------------------

**Access viewer by name:**

.. code-block:: python

    viewer = jd.viewers['1D Spectrum']

**Create new viewer:**

.. code-block:: python

    viewer = jd.new_viewers['Scatter']
    viewer.dataset = 'dataset name'
    viewer.viewer_label = 'my scatterplot'
    viewer()

Working with Subsets
--------------------

**Create subset from region:**

.. code-block:: python

    from regions import CirclePixelRegion, PixCoord

    region = CirclePixelRegion(PixCoord(50, 50), 10)
    jd.load(region, format='Subset', data_label='My Region')

**Import region:**

.. code-block:: python

    from astropy.coordinates import SkyCoord, Angle

    c = SkyCoord('00h37m41.1171s -33d42m58.5745s')

    my_aper_sky = SkyCircularAperture(c, 2 * u.arcsec)
    my_reg_sky = CircleSkyRegion(c, Angle(4, u.arcsec))

    my_regions = [my_aper_sky, my_reg_sky]
    jd.plugins['Subset Tools'].import_region(my_regions, combination_mode='new')

**Get all subsets:**

.. code-block:: python

    subsets = jd.plugins['Subset Tools'].get_regions()


Exporting Data
--------------

.. code-block:: python

    datasets = jd.datasets
    # Returns: {'datasetname': <Data API for spectrum>}

    data_api = jd.datasets['datasetname']
    data = jd.datasets['datasetname'].get_data()

API Hints
---------

**Enable API hints:**

.. code-block:: python

    jd.toggle_api_hints()  # Toggle on/off
    jd.toggle_api_hints(enabled=True)  # Explicitly enable

When enabled, API hints show you the equivalent Python code for UI interactions, making it easy
to automate your workflows.

