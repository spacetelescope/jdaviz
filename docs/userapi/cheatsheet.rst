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

    viewer = jd.new_viewers['Scatter']()

Working with Subsets
--------------------

**Create subset from region:**

.. code-block:: python

    from regions import CirclePixelRegion, PixCoord

    region = CirclePixelRegion(PixCoord(50, 50), 10)
    jd.load(region, format='Subset', data_label='My Region')

**Get all subsets:**

.. code-block:: python

    subsets = jd.plugins['Subset Tools'].get_regions()


Exporting Data
--------------

Coming soon

API Hints
---------

**Enable API hints:**

.. code-block:: python

    jd.toggle_api_hints()  # Toggle on/off
    jd.toggle_api_hints(enabled=True)  # Explicitly enable

When enabled, API hints show you the equivalent Python code for UI interactions, making it easy
to automate your workflows.

