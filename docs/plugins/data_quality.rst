.. _plugins-data_quality:
.. rst-class:: section-icon-mdi-tune-variant

************
Data Quality
************
.. plugin-availability::

Visualize and filter data quality flags.

Description
===========

This plugin allows you to visualize data quality arrays for science data.
The currently supported data quality flag mappings include JWST (all instruments)
and Roman/WFI.

Each science data layer can have one associated data quality layer.
The visibility of the data quality layer can be toggled from the data
dropdown menu, and toggling the science data visibility will do the
same for the data quality layer. The mapping between bits and data quality
flags is defined differently for each mission or instrument, and the
plugin will infer the correct flag mapping from the file metadata.
The opacity of the data quality layer can be changed relative to the
opacity of the science data layer using the slider.

The "Quality Flag" section contains a dropdown for applying a filter to the
visualized bits. Select bits from the dropdown to visualize only flags
containing those bits. The list of data quality flags beneath shows
every flag in the data quality layer in bold, followed by the
decomposed bits in that flag in parentheses. Clicking on a row
will expand to flag to reveal the flag's short name and description,
as well as a visibility toggle for that flag. Click on the color swatch
to select a color for any flag.

**Key Features:**

* Display DQ flag layers
* Filter by specific flags
* Toggle DQ overlay
* Interpret flag meanings

UI Access
=========

.. wireframe-demo::
   :demo: plugins,plugins@1000:open-panel
   :enable-only: plugins
   :plugin-name: Data Quality
   :plugin-panel-opened: false
   :demo-repeat: false

Click the :guilabel:`Data Quality` icon in the plugin toolbar to:

1. Select DQ layer to display
2. Choose specific flags to show
3. Toggle overlay on/off

API Access
==========

.. code-block:: python

    plg = app.plugins['Data Quality']
    plg.flags_filter = [0, 2]

.. plugin-api-refs::
   :module: jdaviz.configs.default.plugins.data_quality.data_quality
   :class: DataQuality
    # Access DQ functionality

See Also
========

* JWST Data Quality documentation
