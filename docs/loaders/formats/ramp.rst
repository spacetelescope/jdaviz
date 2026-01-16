.. _loaders-format-ramp:

:data-types: ramp


******************
Ramp Format
******************

Load Level 1 ramp data products.

Overview
========

The Ramp format is used for loading JWST Level 1 "ramp" data, which contains the
raw accumulated signal measured in multiple reads during an exposure.

Usage
=====

.. code-block:: python

    import jdaviz
    jdaviz.show()

    # Load ramp data
    jdaviz.load('ramp.fits', format='Ramp')

Data Requirements
=================

Ramp data typically contains:

- Multiple reads of the same pixels over time
- 4D data structure: (integrations, groups, y-pixels, x-pixels)
- Detector metadata and timing information

This data format is specific to JWST observations before they are processed through
the calibration pipeline.

UI Access
=========

.. wireframe-demo::
   :demo: loaders,loaders@1000:select-dropdown=Format:Ramp,loaders:highlight=#format-select
   :enable-only: loaders
   :demo-repeat: false

See Also
========

- :doc:`../../rampviz/index` - For information on displaying and analyzing ramp data
