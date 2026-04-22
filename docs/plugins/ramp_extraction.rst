.. _plugins-ramp_extraction:
.. rst-class:: section-icon-mdi-tune-variant

***************
Ramp Extraction
***************
.. plugin-availability::

Extract ramp profiles from detector data.

Description
===========

.. warning::

   Ramp functionality is still under active development. Stay tuned for updates!

The Ramp Extraction plugin collapses spatial dimensions of ramp data to produce
integration-level time series for pixels or regions.

Data products from infrared detectors flow through the official
:ref:`JWST <jwst:user-docs>` or
`Roman <https://roman-pipeline.readthedocs.io/en/latest/>`_ mission pipelines
in levels. Infrared detectors use an "up-the-ramp" readout pattern, which is summarized in the
`JWST documentation <https://jwst-docs.stsci.edu/understanding-exposure-times>`_.

.. note::
    For more information on the JWST and Roman stages/levels, see
    `JWST pipeline stage documentation <https://jwst-pipeline.readthedocs.io/en/stable/jwst/pipeline/main.html#pipelines>`_
    `Roman data pipelines documentation <https://roman-docs.stsci.edu/data-handbook-home/roman-data-pipelines>`_.

The Ramp Extraction plugin is a quick-look tool; it does not yet support every feature of the
mission pipelines. The mission pipelines produce rate images from ramp cubes by fitting the
samples up the ramp while accounting for non-linearity, jumps detected during an integration,
saturation, and detector defects. These data quality checks and corrections are not applied in the
Ramp Extraction plugin. For details on how rate images are derived from ramps, see
the JWST pipeline's :ref:`jwst:ramp_fitting_step` step or the Roman pipeline's
:ref:`romancal:ramp_fitting_step` step.

**Key Features:**

* Extract ramps from spatial regions
* Multiple extraction functions
* Integration visualization
* Uncertainty propagation

UI Access
=========

.. wireframe-demo:: _static/jdaviz-wireframe.html
   :js: jdaviz-wireframe-actions.js
   :css: jdaviz-wireframe.css
   :repeat: false
   :steps-json: [{"action":"show-sidebar","value":"plugins","delay":1500},{"action":"open-panel","value":"Ramp Extraction","delay":1000}]

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

