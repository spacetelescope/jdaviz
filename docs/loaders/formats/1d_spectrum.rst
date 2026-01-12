.. _loaders-format-1d-spectrum:

***************************
1D Spectrum Format
***************************

Load individual one-dimensional spectra.

Overview
========

The 1D Spectrum format is used for loading single spectroscopic observations where
the data varies along one dimension (typically wavelength or frequency).

Usage
=====

.. code-block:: python

    import jdaviz
    jdaviz.show()

    # Load a 1D spectrum
    jdaviz.load('spectrum.fits', format='1D Spectrum')

Data Requirements
=================

The data should contain:

- **Spectral axis**: Wavelength, frequency, or energy values
- **Flux**: The measured intensity at each spectral point
- **Uncertainty** (optional): Error or uncertainty values

Supported File Formats
======================

- FITS files with spectral data
- ASDF files
- ECSV files with spectral columns

The loader automatically detects and parses standard spectroscopic data formats.

Compatible Tools
================

Data loaded with this format can be visualized in:

- **Specviz**: For 1D spectral analysis
- **Mosviz**: As part of multi-object spectroscopy datasets

See Also
========

- :ref:`specviz-displaying` - For information on displaying 1D spectra
