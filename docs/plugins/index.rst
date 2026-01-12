.. _plugins:

*********************
Analysis Plugins
*********************

Jdaviz provides a wide range of data analysis plugins for different types of astronomical data.

.. toctree::
   :maxdepth: 1

   model_fitting
   line_analysis
   line_lists
   gaussian_smooth
   collapse
   moment_maps
   aperture_photometry
   spectral_extraction_2d
   spectral_extraction_3d
   ramp_extraction
   cross_dispersion_profile
   line_profiles
   compass
   catalog_search
   data_quality
   orientation
   footprints
   sonify
   spectral_slice
   ramp_slice
   slit_overlay

Overview
========

Plugins provide specialized analysis capabilities tailored to different data types:

**Spectroscopic Analysis (1D)**
  - Model Fitting
  - Line Analysis
  - Line Lists
  - Gaussian Smooth

**Cube Analysis (3D)**
  - Collapse
  - Moment Maps
  - Spectral Extraction
  - Spectral Slice
  - Sonify Data

**Image Analysis (2D)**
  - Aperture Photometry
  - Line Profiles (XY)
  - Compass
  - Orientation
  - Footprints

**2D Spectroscopy**
  - Spectral Extraction
  - Cross Dispersion Profile
  - Slit Overlay

**Ramp Data**
  - Ramp Extraction
  - Ramp Slice

**Catalog & Quality**
  - Catalog Search
  - Data Quality

Accessing Plugins
=================

Plugins can be accessed from the plugin toolbar in the Jdaviz interface, or
programmatically via the API:

.. code-block:: python

    # Access a plugin
    plugin = app.plugins['Model Fitting']

    # View plugin parameters
    plugin

See the individual plugin pages for detailed usage information.
