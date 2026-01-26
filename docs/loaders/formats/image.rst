.. _loaders-format-image:
.. rst-class:: section-icon-mdi-plus-box

:data-types: image

*********************
Image Format
*********************

Load two-dimensional astronomical images.

Overview
========

The Image format is used for loading 2D astronomical imaging data, such as direct
images from cameras and imagers.

Usage
=====

.. code-block:: python

    import jdaviz
    jdaviz.show()

    # Load an image
    jdaviz.load('image.fits', format='Image')

Data Requirements
=================

The data should be a 2D array where:

- Each pixel represents a spatial position on the sky
- Pixel values represent flux/intensity measurements

Images can be in various coordinate systems and may include WCS (World Coordinate System)
information for relating pixel positions to sky coordinates.

Supported File Formats
======================

- FITS files with 2D image data
- ASDF files with image data
- JWST imaging data (i2d files)
- HST imaging data

UI Access
=========

.. wireframe-demo::
   :demo: loaders,loaders@1000:select-dropdown=Format:Image,loaders:highlight=#format-select
   :enable-only: loaders
   :demo-repeat: false


See Also
========

- :doc:`../../imviz/displayimages` - For information on displaying images
- :doc:`../../imviz/plugins` - For photometric analysis
