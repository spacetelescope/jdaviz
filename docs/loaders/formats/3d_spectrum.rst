.. _loaders-format-3d-spectrum:

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

Compatible Tools
================

Data loaded with this format can be visualized in:

- **Cubeviz**: For 3D spectral cube analysis and visualization

Features Available in Cubeviz
==============================

When viewing 3D spectra in Cubeviz, you can:

- View spatial slices at different wavelengths
- Extract 1D spectra from spatial regions
- Create moment maps
- Collapse the cube along different axes

See Also
========

- :doc:`../../cubeviz/displaycubes` - For information on displaying spectral cubes
- :doc:`../../cubeviz/plugins` - For extracting spectra from cubes and creating moment maps
