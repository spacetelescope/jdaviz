.. _plugins-line_lists:

**********
Line Lists
**********

Display and manage spectral line identifications.

Description
===========

The Line Lists plugin loads and displays spectral line identifications from
catalogs. Lines are overlaid on spectrum viewers to aid in feature identification
and analysis.

**Key Features:**

* Load predefined line lists (atomic, molecular)
* Custom line list import
* Toggle line visibility
* Redshift correction
* Color customization
* Filter by wavelength range

**Available in:** Specviz, Cubeviz, Specviz2d, Mosviz

UI Access
=========

Click the :guilabel:`Line Lists` icon in the plugin toolbar to:

1. Select line lists to load
2. Set redshift for line positions
3. Toggle line display on/off
4. Customize line colors

API Access
==========

.. code-block:: python

    plg = app.plugins['Line Lists']

    # Load a line list
    plg.load_line_list('SDSS')

    # Set redshift
    plg.set_redshift(0.05)

.. plugin-api-refs::
   :module: jdaviz.configs.default.plugins.line_lists.line_lists
   :class: LineListTool

See Also
========

* :ref:`line-lists` - Detailed line lists documentation
