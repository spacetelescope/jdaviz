.. _plugins-line_lists:
.. rst-class:: section-icon-mdi-tune-variant

**********
Line Lists
**********
.. plugin-availability::

Display and manage spectral line identifications.

Description
===========

The Line Lists plugin loads and displays spectral line identifications from
catalogs. Lines are overlaid on spectrum viewers to aid in feature identification
and analysis.

.. warning::

   The Line Lists plugin is still under active development. The API is not
   yet fully exposed, and spectral lines can currently
   only be displayed in a single spectrum viewer at a time.

**Key Features:**

* Load predefined line lists (atomic, molecular)
* Custom line list import
* Toggle line visibility
* Redshift correction
* Color customization
* Filter by wavelength range

UI Access
=========

.. wireframe-demo::
   :demo: plugins,plugins@1000:open-panel
   :enable-only: plugins
   :plugin-name: Line Lists
   :demo-repeat: false

Click the :guilabel:`Line Lists` icon in the plugin toolbar to:

1. Select line lists to load
2. Set redshift for line positions
3. Toggle line display on/off
4. Customize line colors

API Access
==========

The public API for the this plugin is in development

.. plugin-api-refs::
   :module: jdaviz.configs.default.plugins.line_lists.line_lists
   :class: LineListTool

See Also
========

* :ref:`loaders-format-line-list` - Importing custom line lists
* :ref:`line-lists` - Detailed line lists documentation
