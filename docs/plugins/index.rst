.. _plugins:
.. rst-class:: section-icon-mdi-tune-variant

*********************
Analysis Plugins
*********************

Jdaviz provides a wide range of data analysis plugins for different types of astronomical data.
  

Overview
========

Plugins provide specialized analysis capabilities tailored to different data types:

.. toctree::
  :maxdepth: 1
  :caption: Spectroscopic Analysis (1D)

  model_fitting
  line_analysis
  line_lists
  spectral_lines
  gaussian_smooth

.. toctree::
  :maxdepth: 1
  :caption: Cube Analysis (3D)

  collapse
  moment_maps
  3d_spectral_extraction
  spectral_slice
  sonify

.. toctree::
  :maxdepth: 1
  :caption: Image Analysis (2D)

  aperture_photometry
  image_profiles
  compass
  orientation
  footprints


.. toctree::
  :maxdepth: 1
  :caption: 2D Spectroscopy

  2d_spectral_extraction
  cross_dispersion_profile

.. toctree::
  :maxdepth: 1
  :caption: Ramp Data

  ramp_extraction
  ramp_slice

.. toctree::
  :maxdepth: 1
  :caption: Catalog & Quality

  catalog_search
  data_quality

UI Access
=========

.. guidestar-demo:: _static/jdaviz-wireframe.html
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

Plugin extensions
=================

.. toctree::
   :maxdepth: 1
   
   extensions

