.. _loaders-source-object:

************************
Loading Python Objects
************************

The object loader allows you to load data directly from Python objects in memory.

Usage
=====

.. code-block:: python

    import jdaviz
    from specutils import Spectrum1D
    import astropy.units as u
    import numpy as np

    # Create a spectrum object
    wavelength = np.linspace(5000, 6000, 1000) * u.AA
    flux = np.random.random(1000) * u.Jy
    spec = Spectrum1D(spectral_axis=wavelength, flux=flux)

    jdaviz.show()

    # Using load() directly
    jdaviz.load(spec, format='1D Spectrum')

    # Using loaders API
    ldr = jdaviz.loaders['object']
    ldr.object = spec
    ldr.format = '1D Spectrum'
    ldr.load()

Supported Object Types
======================

The object loader supports various astronomical data object types:

- :class:`~specutils.Spectrum1D` - Individual 1D spectra
- :class:`~specutils.SpectrumCollection` - Collections of spectra
- :class:`~astropy.nddata.NDData` - Generic N-dimensional data
- :class:`~astropy.nddata.CCDData` - CCD image data
- NumPy arrays (with appropriate metadata)

See :ref:`loaders-formats` for information on how to specify the format parameter.
