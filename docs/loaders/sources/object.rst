:excl_platforms: desktop mast

.. _loaders-source-object:

************************
Loading Python Objects
************************

The object loader allows you to load data directly from Python objects in memory.


Supported Object Types
======================

The object loader supports various astronomical data object types:

- :class:`~specutils.Spectrum1D` - Individual 1D spectra
- :class:`~specutils.SpectrumCollection` - Collections of spectra
- :class:`~astropy.nddata.NDData` - Generic N-dimensional data
- :class:`~astropy.nddata.CCDData` - CCD image data
- NumPy arrays (with appropriate metadata)

See :ref:`loaders-formats` for information on how to specify the format parameter.

UI Access
=========

.. wireframe-demo::
   :demo: loaders,loaders@1000:select-dropdown=Source:object,loaders:highlight=#source-select
   :enable-only: loaders
   :demo-repeat: false

Note that the object loader is only available when there is API access (e.g., in Jupyter notebooks),
but although there is a UI, requires API access to be functional.

API Access
==========

.. code-block:: python

    import jdaviz as jd
    from specutils import Spectrum1D
    import astropy.units as u
    import numpy as np

    # Create a spectrum object
    wavelength = np.linspace(5000, 6000, 1000) * u.AA
    flux = np.random.random(1000) * u.Jy
    spec = Spectrum1D(spectral_axis=wavelength, flux=flux)

    jd.show()

    # Using load() directly
    jd.load(spec, format='1D Spectrum')

    # Using loaders API
    ldr = jd.loaders['object']
    ldr.object = spec
    ldr.format = '1D Spectrum'
    ldr.load()