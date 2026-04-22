.. _loaders-format-2d-spectrum:
.. rst-class:: section-icon-mdi-plus-box

:data-types: 2d

***************************
2D Spectrum Format
***************************

Load two-dimensional spectroscopic data.

Overview
========

The 2D Spectrum format is used for loading spectroscopic data where the flux varies
along two dimensions - typically the dispersion (wavelength) direction and the
spatial (cross-dispersion) direction.

Usage
=====

.. code-block:: python

    import jdaviz
    jdaviz.show()

    # Load a 2D spectrum
    jdaviz.load('spectrum2d.fits', format='2D Spectrum')

Data Requirements
=================

The data should be a 2D array where:

- One axis represents the spectral (dispersion) direction
- The other axis represents the spatial (cross-dispersion) direction
- Pixel values represent flux measurements

Common examples include long-slit spectroscopy and grism spectroscopy data.

Supported File Formats
======================

- FITS files with 2D spectral images
- JWST pipeline products (s2d files)
- HST grism data

UI Access
=========

.. wireframe-demo:: _static/jdaviz-wireframe.html
   :js: jdaviz-wireframe-actions.js
   :css: jdaviz-wireframe.css
   :repeat: false
   :steps-json: [{"action":"show-sidebar","value":"loaders","delay":1500},{"action":"select-dropdown","value":"Format:2D Spectrum","delay":1000},{"action":"highlight","target":"#format-select","delay":1500}]

See Also
========

- :ref:`specviz2d-displaying` - For information on displaying 2D spectra
- :ref:`specviz2d-spectral-extraction` - For extracting 1D spectra from 2D data
