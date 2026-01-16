.. _loaders-formats:

*************************
Data Formats
*************************

When loading data into Jdaviz, you specify a format that determines how the data
will be parsed and which tools can visualize it:

.. toctree::
   :maxdepth: 1

   1d_spectrum
   2d_spectrum
   3d_spectrum
   image
   catalog
   ramp

Each format has specific requirements for the data structure. The format determines
which viewers and analysis tools are available for that data.

See :ref:`loaders-sources` for information on different ways to load data.

UI Access
=========

.. wireframe-demo::
   :initial: loaders
   :demo: loaders:highlight=#format-select
   :enable-only: loaders
   :demo-repeat: false

API Access
==========

You can specify the data format programmatically when loading data:

.. code-block:: python

    ldr = jdaviz.loaders['file']
    ldr.filename = 'mydata.fits'
    ldr.format = '1D Spectrum'  # Specify the desired format
    ldr.load()

or by passing as a keyword argument to the load function:

.. code-block:: python

    jdaviz.load('mydata.fits', format='1D Spectrum')