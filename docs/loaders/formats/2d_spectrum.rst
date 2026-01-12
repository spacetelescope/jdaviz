.. _loaders-format-2d-spectrum:

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

Compatible Tools
================

Data loaded with this format can be visualized in:

- **Specviz2d**: For 2D spectral analysis and extraction
- **Mosviz**: As part of multi-object spectroscopy datasets

See Also
========

- :ref:`specviz2d-displaying` - For information on displaying 2D spectra
- :ref:`specviz2d-spectral-extraction` - For extracting 1D spectra from 2D data
