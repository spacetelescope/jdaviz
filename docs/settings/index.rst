.. _settings:
.. rst-class:: section-icon-mdi-cog

*******************
Settings & Options
*******************

Jdaviz provides flexible configuration options for customizing your analysis environment:

**Plot Options**
  Control the visual appearance of plots including colors, line styles, markers,
  and other display properties.

**Display Units**
  Configure the units used for displaying spectral axes (wavelength, frequency, energy)
  and flux values.

.. toctree::
   :maxdepth: 1

   plot_options
   display_units


UI Access
=========

.. wireframe-demo:: _static/jdaviz-wireframe.html
   :js: jdaviz-wireframe-actions.js
   :css: jdaviz-wireframe.css
   :repeat: false
   :init-steps-json: [{"action":"show-sidebar","value":"settings"}]

See Also
========

- :ref:`display` - For information on customizing notebook display layout
