.. _plugins-data_quality:

************
Data Quality
************

.. plugin-availability::

Visualize and filter data quality flags.

Description
===========

The Data Quality plugin displays and manages data quality (DQ) flags from JWST
and HST observations. It allows visualization of flagged pixels and filtering
based on quality criteria.

**Key Features:**

* Display DQ flag layers
* Filter by specific flags
* Toggle DQ overlay
* Interpret flag meanings

**Available in:** Imviz, Cubeviz

UI Access
=========

Click the :guilabel:`Data Quality` icon in the plugin toolbar to:

1. Select DQ layer to display
2. Choose specific flags to show
3. Toggle overlay on/off

API Access
==========

.. code-block:: python

    plg = app.plugins['Data Quality']

.. plugin-api-refs::
   :module: jdaviz.configs.default.plugins.data_quality.data_quality
   :class: DataQuality
    # Access DQ functionality

See Also
========

* JWST Data Quality documentation
