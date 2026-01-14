.. _settings:
.. rst-class:: section-icon-mdi-cog

*******************
Settings & Options
*******************

Configure plot appearance, display units, and other viewer options.

.. toctree::
   :maxdepth: 1

   plot_options
   display_units

Overview
========

Jdaviz provides flexible configuration options for customizing your analysis environment:

**Plot Options**
  Control the visual appearance of plots including colors, line styles, markers,
  and other display properties.

**Display Units**
  Configure the units used for displaying spectral axes (wavelength, frequency, energy)
  and flux values.

Accessing Settings
==================

Settings can be accessed through:

**Plot Options Plugin**: Available in the plugin toolbar, provides controls for
customizing viewer appearance.

**Programmatic Access**: Configure settings via the API:

.. code-block:: python

    # Access plot options
    plot_options = app.plugins['Plot Options']

    # Configure display
    plot_options.line_color = 'red'
    plot_options.line_width = 2

See Also
========

- :ref:`display` - For information on customizing notebook display layout
- Individual settings pages for detailed configuration options
