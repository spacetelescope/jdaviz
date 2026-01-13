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

Compatible Tools
================

Data loaded with this format can be visualized in:

- **Rampviz**: For visualizing and analyzing raw ramp data

Features Available in Rampviz
==============================

When viewing ramp data in Rampviz, you can:

- View individual reads and groups
- Examine ramp profiles for individual pixels
- Identify cosmic ray hits and other artifacts
- Assess data quality before calibration

See Also
========

- :doc:`../../rampviz/index` - For information on displaying and analyzing ramp data
