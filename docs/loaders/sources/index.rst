.. _loaders-sources:

*************************
Data Sources
*************************

Jdaviz can load data from various sources. Select a source below to learn more:

.. toctree::
   :maxdepth: 1

   file
   file_drop
   url
   object
   astroquery
   virtual_observatory

Each source can load data in various formats. See :ref:`loaders-formats` for information
on supported data formats.

UI Access
=========

.. wireframe-demo::
   :demo: loaders,loaders:select-tab=Data
   :enable-only: loaders
   :demo-repeat: false

API Access
==========

.. code-block:: python

    import jdaviz as jd
    jd.show()

    # Access loaders
    loaders = jd.loaders

    # Get list of available loaders
    print(loaders)

    # Use a specific loader
    ldr = loaders['file']  # Or file drop, url, object, astroquery, vo

    # Configure loading options
    ldr.filename = 'my_data.fits'  # or ldr.url, ldr.object, etc.
    ldr.format = '1D Spectrum'

    # Import the data
    ldr.load()