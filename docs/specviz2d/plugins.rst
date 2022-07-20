.. _specviz2d-plugins:

*********************
Data Analysis Plugins
*********************

The Specviz2D data analysis plugins are meant to aid quick-look analysis
of 2D spectroscopic data. All plugins are accessed via the :guilabel:`plugin`
icon in the upper right corner of the Specviz application. 

.. _specviz2d-metadata-viewer:

Metadata Viewer
===============

.. seealso::

    :ref:`Metadata Viewer <imviz_metadata-viewer>`
        Imviz documentation on using the metadata viewer.

.. _specviz2d-plot-options:

Plot Options
============

.. seealso::

    :ref:`Spectral Plot Options <specviz-plot-settings>`
        Documentation on further details regarding the plot setting controls.

.. _specviz2d-subset-plugin:

Subset Tools
============

.. seealso::

    :ref:`Subset Tools <imviz-subset-plugin>`
        Imviz documentation describing the concept of subsets in Jdaviz.

.. _specviz2d-spectral-extraction:

Spectral Extraction
===================

The Spectral Extraction plugin exposes `specreduce <https://specreduce.readthedocs.io>`_
methods for tracing, background subtraction, and spectral extraction from 2D spectra.

Trace
-----

The first section of the plugin allows for creating and visualizing 
`specreduce Trace <https://specreduce.readthedocs.io/en/latest/#module-specreduce.tracing>`_
objects.

Trace objects created outside of jdaviz can be loaded into the app via::

    viz.app.add_data(my_trace)

and then added to the viewer through the data menu.


To create a new trace in the plugin, choose the desired "Trace Type", any input arguments,
optionally override the name of the resulting data entry, and click "Create".  This will run
the respective specreduce function and load the resulting Trace object into the app
(and 2d spectrum viewer).  This trace will then be available to be used as input for the
background subtraction and spectral extraction steps of the plugin.

Once trace objects are loaded into the app, they can be offset (in the cross-dispersion direction)
by selecting the trace label, entering an offset, and overwriting the existing data entry with the
modified trace.

.. _specviz2d-gaussian-smooth:

Gaussian Smooth
===============

.. seealso::

    :ref:`Gaussian Smooth <gaussian-smooth>`
        Specviz documentation on Gaussian Smooth.

.. _specviz2d-model-fitting:

Model Fitting
=============

.. seealso::

    :ref:`Model Fitting <specviz-model-fitting>`
        Specviz documentation on Model Fitting.


.. _specviz2d-unit-conversion:

Unit Conversion
===============

.. seealso::

    :ref:`Unit Conversion <unit-conversion>`
        Specviz documentation on Unit Conversion.


.. _specviz2d-line-lists:

Line Lists
==========

.. seealso::

    :ref:`Line Lists <line-lists>`
        Specviz documentation on Line Lists.
        

.. _specviz2d-line-analysis:

Line Analysis
=============

.. seealso::

    :ref:`Line Analysis <line-analysis>`
        Specviz documentation on Line Analysis.

.. _specviz2d-export-plot:

Export Plot
===========

This plugin allows exporting the plot in a given viewer to various image formats.
