.. _loaders-formats:

*************************
Data Formats
*************************

Jdaviz can parse data in various astronomical formats. Select a format below to learn more:

.. toctree::
   :maxdepth: 1

   1d_spectrum
   2d_spectrum
   3d_spectrum
   image
   catalog
   ramp

Overview
========

When loading data into Jdaviz, you specify a format that determines how the data
will be parsed and which tools can visualize it:

- **1D Spectrum**: Individual one-dimensional spectra (Specviz, Mosviz)
- **2D Spectrum**: Two-dimensional spectroscopic data (Specviz2d, Mosviz)
- **3D Spectrum**: Three-dimensional spectral cubes (Cubeviz)
- **Image**: Two-dimensional astronomical images (Imviz, Mosviz)
- **Catalog**: Astronomical source catalogs (coming soon)
- **Ramp**: JWST Level 1 ramp data (Rampviz)

Each format has specific requirements for the data structure. The format determines
which viewers and analysis tools are available for that data.

See :ref:`loaders-sources` for information on different ways to load data.
