.. _plugins-ramp_extraction:
.. _rampviz-ramp-extraction:

***************
Ramp Extraction
***************

Extract ramp profiles from detector data.

Description
===========

The Ramp Extraction plugin collapses spatial dimensions of ramp data to produce
integration-level time series for pixels or regions.

**Key Features:**

* Extract ramps from spatial regions
* Multiple extraction functions
* Integration visualization
* Uncertainty propagation

**Available in:** Rampviz

UI Access
=========

Click the :guilabel:`Ramp Extraction` icon in the plugin toolbar to:

1. Select ramp dataset
2. Choose spatial region
3. Select extraction function
4. Extract ramp profile

API Access
==========

.. code-block:: python

    plg = rampviz.plugins['Ramp Extraction']
    plg.aperture = 'Subset 1'
    plg.extract()

.. plugin-api-refs::
   :module: jdaviz.configs.rampviz.plugins.ramp_extraction.ramp_extraction
   :class: RampExtraction

See Also
========

* :ref:`rampviz-ramp-extraction` - Ramp extraction documentation
