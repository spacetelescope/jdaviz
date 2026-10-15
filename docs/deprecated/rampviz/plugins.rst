*********************
Data Analysis Plugins
*********************

.. include:: ../_templates/deprecated_config_banner.rst



.. _rampviz-metadata-viewer:

Metadata Viewer
===============

.. seealso::

    :ref:`Metadata Viewer <imviz-metadata-viewer>`
        Documentation on using the metadata viewer.


.. _rampviz-plot-options:

Plot Options
============

This plugin gives access to per-viewer and per-layer plotting options.
To show axes on image viewers, toggle on the "Show axes" option at the bottom of the plugin.

.. seealso::

    :ref:`Image Plot Options <imviz-display-settings>`
        Documentation on Imviz display settings in the Jdaviz viewers.

.. _rampviz-subset-plugin:

Subset Tools
============

.. seealso::

    :ref:`Subset Tools <imviz-subset-plugin>`
        Imviz documentation describing the concept of subsets in Jdaviz.


Markers
=======

.. seealso::

    :ref:`Markers <markers-plugin>`
        Imviz documentation describing the markers plugin.

.. _rampviz-slice:

Slice
=====

.. seealso::

    :ref:`Slice <slice>`
        Documentation on using the Slice plugin.

.. _ramp-extraction:

Ramp Extraction
===============

Extract a ramp from a ramp cube.

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
