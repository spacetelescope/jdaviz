.. _plugins:
.. rst-class:: section-icon-mdi-tune-variant

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
   2d_spectral_extraction
   3d_spectral_extraction
   ramp_extraction
   cross_dispersion_profile
   image_profiles
   compass
   catalog_search
   data_quality
   orientation
   footprints
   sonify
   spectral_slice
   ramp_slice
   extensions

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
  - Image Profiles (XY)
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

UI Access
=========

.. wireframe-demo:: _static/jdaviz-wireframe.html
   :repeat: true
   :init-steps-json: [{"action":"show-sidebar","value":"plugins"},{"action":"disable-toolbar-except","value":"plugins"}]

API Access
==========

Plugins can be accessed from the plugin toolbar in the Jdaviz interface, or
programmatically via the API:

.. code-block:: python

    # Access a plugin
    plg = jd.plugins['Model Fitting']

    # Show in tray
    plg.open_in_tray()

    # Show in-line in notebook
    plg.show()

See the individual plugin pages for detailed usage information.
