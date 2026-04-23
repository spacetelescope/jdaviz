.. _loaders-format-3d-spectrum:
.. rst-class:: section-icon-mdi-plus-box

:data-types: 3d

***************************
3D Spectrum Format
***************************

Load three-dimensional spectroscopic data cubes.

Overview
========

The 3D Spectrum format is used for loading spectroscopic data cubes where flux varies
along three dimensions - typically two spatial dimensions and one spectral dimension.

Usage
=====

.. code-block:: python

    import jdaviz
    jdaviz.show()

    # Load a 3D spectrum cube
    jdaviz.load('cube.fits', format='3D Spectrum')

Data Requirements
=================

The data should be a 3D array where:

- Two axes represent spatial dimensions (X, Y positions on sky)
- One axis represents the spectral dimension (wavelength/frequency)
- Pixel values represent flux measurements

This format is commonly used for Integral Field Unit (IFU) spectroscopy data.

Supported File Formats
======================

- FITS files with 3D data cubes
- JWST MIRI and NIRSpec IFU data (s3d files)
- Other IFU instrument data cubes

UI Access
=========

.. wireframe-demo:: _static/jdaviz-wireframe.html
   :js: jdaviz-wireframe-actions.js
   :css: jdaviz-wireframe.css
   :repeat: false
   :steps-json: [{"action": "show-sidebar", "value": "loaders", "delay": 1500, "caption": "Open the data loader"}, {"action": "select-dropdown", "value": "Format:3D Spectrum", "delay": 1000, "caption": "Set format to 3D Spectrum"}, {"action": "highlight", "target": "#format-select", "delay": 1500}]

See Also
========

- :doc:`../../cubeviz/displaycubes` - For information on displaying spectral cubes
- :doc:`../../cubeviz/plugins` - For extracting spectra from cubes and creating moment maps
