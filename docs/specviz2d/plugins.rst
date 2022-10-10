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

    :ref:`Plot Options <specviz-plot-options>`
        Specviz documentation on the plot options plugin.

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

To interact with the plugin via the API in a notebook, access the plugin object via::

  sp_ext = viz.app.get_tray_item_from_name('spectral-extraction')


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

Trace objects created outside of jdaviz can be loaded into the app via :meth:`~jdaviz.configs.specviz2d.helper.Specviz2d.load_trace`:

  viz.load_trace(my_trace, data_label="my trace")

and then added to the viewer through the data menu.

Once trace objects are loaded into the app, they can be offset (in the cross-dispersion direction)
by selecting the trace label, entering an offset, and overwriting the existing data entry (or
creating a new one) with the modified trace.

To export and access the specreduce Trace object defined in the plugin, call :meth:`~jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction.SpectralExtraction.export_trace`::

  trace = sp_ext.export_trace()

To import the parameters from a specreduce Trace object, whether it's new or was exported and modified in the notebook, call :meth:`~jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction.SpectralExtraction.import_trace`::

  sp_ext.import_trace(trace)

Background
----------

The background step of the plugin allows for creating background and background-subtracted
images via `specreduce.background <https://specreduce.readthedocs.io/en/latest/#module-specreduce.background>`_.

Once you interact with any of the inputs in the background step or hover over that area
of the plugin, the live visualization in the 2d spectrum viewer will change to show the center 
(dotted line) and edges (solid lines) of the background region(s).  The 1D representation of the
background will also be visualized in the 1D spectrum viewer (thin solid line).

Choose between creating the background around the trace defined in the Trace section, or around a "Manual" flat trace.

To visualize the resulting background or background-subtracted image, click on the respective panel,
and choose a label for the new data entry.  The exported images will now appear in the data dropdown
menu in the 2D spectrum viewer, and can be :ref:`exported into the notebook via the API <specviz2d-export-data-2d>`.  
To refine the trace based on the background-subtracted image, return
to the Trace step and select the exported background-subtracted image as input. 

To export and access the specreduce Background object defined in the plugin, call :meth:`~jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction.SpectralExtraction.export_bg`::

  bg = sp_ext.export_bg()

To access the background image, background spectrum, or background-subtracted image as a :class:`~specutils.Spectrum1D` object,
call :meth:`~jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction.SpectralExtraction.export_bg_img`,
:meth:`~jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction.SpectralExtraction.export_bg_spectrum`,
or :meth:`~jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction.SpectralExtraction.export_bg_sub`, respectively.

To import the parameters from a specreduce Background object into the plugin, whether it's new or was exported and modified in the notebook, call :meth:`~jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction.SpectralExtraction.import_bg`::

  sp_ext.import_bg(bg)

Extract
-------

The extraction step of the plugin extracts a 1D spectrum from an input 2D spectrum via
`specreduce.extract <https://specreduce.readthedocs.io/en/latest/#module-specreduce.extract>`_.

Once you interact with any of the inputs in the extract step or hover over that area
of the plugin, the live visualization will change to show the center (dotted line) and
edges (solid lines) of the extraction region.

The input 2D spectrum defaults to "From Plugin", which will use the settings defined in the Background
step to create a background-subtracted image without needing to export it into the app itself.
To use a different 2D spectrum loaded in the app (or exported from the Background step), choose
that from the dropdown instead.  To skip background subtraction, choose the original 2D spectrum
as input.

To visualize or export the resulting 2D spectrum, provide a data label and click "Extract".  The 
resulting spectrum object can be :ref:`accessed from the API <specviz2d-export-data-1d>` in the same
way as any other data product in the spectrum viewer.

To export and access the specreduce extraction object defined in the plugin, call :meth:`~jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction.SpectralExtraction.export_extract`::

  ext = sp_ext.export_extract()

To access the extracted spectrum as a :class:`~specutils.Spectrum1D` object, call :meth:`~jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction.SpectralExtraction.export_extract_spectrum`.

To import the parameters from a specreduce extraction object (either a new object, or an exported one modified in the notebook) into the plugin, call :meth:`~jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction.SpectralExtraction.import_extract`::

  sp_ext.import_extract(ext)


.. note::

    Horne extraction uses uncertainties on the input 2D spectrum. If the
    spectrum uncertainties are not explicitly assigned a type, they are assumed
    to be standard deviation uncertainties.


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

.. note::
    The line lists plugin is currently disabled if the 1D spectrum was automatically extracted
    and/or the 1D spectrum's x-axis is in pixels.

.. seealso::

    :ref:`Line Lists <line-lists>`
        Specviz documentation on Line Lists.
        

.. _specviz2d-line-analysis:

Line Analysis
=============

.. note::
    The line analysis plugin is currently disabled if the 1D spectrum was automatically extracted
    and/or the 1D spectrum's x-axis is in pixels.

.. seealso::

    :ref:`Line Analysis <line-analysis>`
        Specviz documentation on Line Analysis.

.. _specviz2d-export-plot:

Export Plot
===========

This plugin allows exporting the plot in a given viewer to various image formats.
