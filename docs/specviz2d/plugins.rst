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

Once you interact with any of the inputs in the extract step or hover over that area
of the plugin, the live visualization will change to show the trace as a solid line.

To create a new trace in the plugin, choose the desired "Trace Type" and edit any input arguments.
A preview of the trace will update in real time in the 2D spectrum viewer.

To export the trace as a data object into the 2D spectrum viewer (to access via the API or to 
adjust plotting options), open the "Export Trace" panel, choose a label for the new data entry,
and click "Create".  Note that this step is not required to create an extraction with simple
workflows.

Trace objects created outside of jdaviz can be loaded into the app via::

    viz.app.add_data(my_trace)

and then added to the viewer through the data menu.

Once trace objects are loaded into the app, they can be offset (in the cross-dispersion direction)
by selecting the trace label, entering an offset, and overwriting the existing data entry (or
creating a new one) with the modified trace.

Background
----------

The background step of the plugin allows for creating background and background-subtracted
images via `specreduce.background <https://specreduce.readthedocs.io/en/latest/#module-specreduce.background>`_.

Once you interact with any of the inputs in the background step or hover over that area
of the plugin, the live visualization will change to show the center (dotted line) and edges
(solid lines) of the background region(s).  Choose between creating the background
around the trace defined in the Trace section, or around a "Manual" flat trace.

To visualize the resulting background or background-subtracted image, click on the respective panel,
and choose a label for the new data entry.  The exported images will now appear in the data dropdown
menu in the 2D spectrum viewer.  To refine the trace based on the background-subtracted image, return
to the Trace step and select the exported background-subtracted image as input. 

Extract
-------

The extraction step of the plugin extracts a 1D spectrum from an input 2D spectrum via
`specreduce.extract <https://specreduce.readthedocs.io/en/latest/#module-specreduce.extract>`_.

Once you interact with any of the inputs in the extract step or hover over that area
of the plugin, the live visualization will change to show the center (dotted line) and
edges (solid lines) of the extraction region.```

The input 2D spectrum defaults to "From Plugin", which will use the settings defined in the Background
step to create a background-subtracted image without needing to export it into the app itself.
To use a different 2D spectrum loaded in the app (or exported from the Background step), choose
that from the dropdown instead.  To skip background subtraction, choose the original 2D spectrum
as input.

To visualize or export the resulting 2D spectrum, provide a data label and click "Extract".  The 
resulting spectrum object can be accessed from the API in the same way as any other
data product in the spectrum viewer.


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
