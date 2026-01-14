.. _viewers:
.. rst-class:: section-icon-mdi-plus-box

*******
Viewers
*******

Jdaviz provides specialized viewers for different types of astronomical data.

.. toctree::
   :maxdepth: 1

   spectrum_1d
   spectrum_2d
   image_2d
   profile_1d
   table
   scatter
   histogram
   extensions

Overview
========

Viewers display your data in interactive, customizable plots:

**Spectrum Viewers**
  - **1D Spectrum**: Display one-dimensional spectra
  - **2D Spectrum**: Display two-dimensional spectroscopic data
  - **Profile 1D**: Display extracted spectral profiles

**Image Viewers**
  - **Image 2D**: Display astronomical images with WCS support

**Data Viewers**
  - **Table**: Display tabular data
  - **Scatter**: Create scatter plots from data
  - **Histogram**: View data distributions

Creating Viewers
================

In deconfigged mode, viewers are created automatically based on the data format you load:

.. code-block:: python

    import jdaviz
    jdaviz.show()

    # Automatically creates appropriate viewer
    jdaviz.load('spectrum.fits', format='1D Spectrum')

You can also create viewers programmatically:

.. code-block:: python

    # Create a new viewer
    viewer = app.create_viewer('spectrum-viewer')

See the individual viewer pages for detailed usage information.
