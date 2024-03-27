.. _specviz2d-plugins:

*********************
Data Analysis Plugins
*********************

The Specviz2D data analysis plugins are meant to aid quick-look analysis
of 2D spectroscopic data. All plugins are accessed via the :guilabel:`plugin`
icon in the upper right corner of the Specviz2d application.

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

Markers
=======

.. seealso::

    :ref:`Markers <markers-plugin>`
        Imviz documentation describing the markers plugin.

.. _specviz2d-spectral-extraction:

Spectral Extraction
===================

The Spectral Extraction plugin exposes `specreduce <https://specreduce.readthedocs.io>`_
methods for tracing, background subtraction, and spectral extraction from 2D spectra.

To interact with the plugin via the API in a notebook, access the plugin object via:

.. code-block:: python

  sp_ext = specviz2d.plugins['Spectral Extraction']


Trace
-----

The first section of the plugin allows for creating and visualizing
:py:class:`specreduce.tracing.Trace` objects.

Once you interact with any of the inputs in the extract step or hover over that area
of the plugin, the live visualization will change to show the trace as a solid line
in the 2D spectrum viewer.

To create a new trace in the plugin, choose the desired "Trace Type" and edit any input arguments.
A preview of the trace will update in real time in the 2D spectrum viewer.

To export the trace as a data object into the 2D spectrum viewer (to access via the API or to
adjust plotting options), open the "Export Trace" panel, choose a label for the new data entry,
and click "Create".  Note that this step is not required to create an extraction with simple
workflows.

Suppose you have 2D spectra of an extended source, and you have already created a trace that follows the
bright central region of the source. It is possible to create a new trace, with the same 2D
shape as the trace of the central region, but offset in the spatial direction. This might be useful
for extracting spectra from the faint outer regions of the extended source, while using a trace computed from the
brighter inner region. You can create a new trace based on the existing trace by clicking
the "Trace" dropdown and selecting the existing trace. Then, offset it in the spatial direction by clicking or entering
the spatial offset, and save it by creating a new trace or overwriting the existing trace entry.

From the API
^^^^^^^^^^^^

Trace parameters can be set from the notebook by accessing the plugin.

.. code-block:: python

    sp_ext.trace_type = 'Polynomial'
    sp_ext.trace_order = 2
    sp_ext.trace_window = 10
    sp_ext.trace_peak_method = 'Gaussian'

To export and access the specreduce Trace object defined in the plugin, call
:py:meth:`~jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction.SpectralExtraction.export_trace`:

.. code-block:: python

    trace = sp_ext.export_trace()

Trace objects created outside of jdaviz can be loaded into the app via :py:meth:`~jdaviz.configs.specviz2d.helper.Specviz2d.load_trace`:

.. code-block:: python

    specviz2d.load_trace(my_trace, data_label="my trace")

or directly into the plugin as

.. code-block:: python

    sp_ext.import_trace(my_trace)


Background
----------

The background step of the plugin allows for creating background and background-subtracted
images via :py:mod:`specreduce.background`.

Once you interact with any of the inputs in the background step or hover over that area
of the plugin, the live visualization in the 2D spectrum viewer will change to show the center
(dotted line) and edges (solid lines) of the background region(s).  The 1D representation of the
background will also be visualized in the 1D spectrum viewer (thin, solid line).

Backgrounds can either be created around the trace defined in the earlier Trace section or around a new,
flat trace by selecting "Manual" in the Background Type dropdown.

To visualize the resulting background or background-subtracted image, click on the respective panel,
and choose a label for the new data entry.  The exported images will now appear in the data dropdown
menu in the 2D spectrum viewer.
To refine the trace based on the background-subtracted image, return
to the Trace step and select the exported background-subtracted image as input.

From the API
^^^^^^^^^^^^

Background parameters can be set from the notebook by accessing the plugin.

.. code-block:: python

    sp_ext.bg_type = 'TwoSided'
    sp_ext.bg_separation = 8
    sp_ext.bg_width = 6

To export and access the specreduce Background object defined in the plugin, call :py:meth:`~jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction.SpectralExtraction.export_bg`:

.. code-block:: python

  bg = sp_ext.export_bg()

To access the background image, background spectrum, or background-subtracted image as a :class:`~specutils.Spectrum` object,
call :py:meth:`~jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction.SpectralExtraction.export_bg_img`,
:py:meth:`~jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction.SpectralExtraction.export_bg_spectrum`,
or :py:meth:`~jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction.SpectralExtraction.export_bg_sub`, respectively.

To import the parameters from a specreduce Background object into the plugin, whether it's new or was exported and modified in the notebook, call :py:meth:`~jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction.SpectralExtraction.import_bg`:

.. code-block:: python

  sp_ext.import_bg(bg)

Extract
-------

The extraction step of the plugin extracts a 1D spectrum from an input 2D spectrum via
:py:mod:`specreduce.extract`.

Once you interact with any of the inputs in the extract step or hover over that area
of the plugin, the live visualization will change to show the center (dotted line) and
edges (solid lines) of the extraction region.

The input 2D spectrum defaults to "From Plugin", which will use the settings defined in the Background
step to create a background-subtracted image without needing to export it into the app itself.
To use a different 2D spectrum loaded in the app (or exported from the Background step), choose
that from the dropdown instead.  To skip background subtraction, choose the original 2D spectrum
as input.

To visualize or export the resulting 2D spectrum, provide a data label and click "Extract".
The resulting spectrum object can be :ref:`accessed from the API <specviz2d-export-data-1d>` in the same
way as any other data product in the spectrum viewer.

From the API
^^^^^^^^^^^^

Extraction parameters can be set from the notebook by accessing the plugin.

.. code-block:: python

    sp_ext.ext_type = 'Boxcar'
    sp_ext.ext_width = 8

To export and access the specreduce extraction object defined in the plugin, call :py:meth:`~jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction.SpectralExtraction.export_extract`:

.. code-block:: python

  ext = sp_ext.export_extract()

To access the extracted spectrum as a :class:`~specutils.Spectrum` object, call :py:meth:`~jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction.SpectralExtraction.export_extract_spectrum`.

To import the parameters from a specreduce extraction object (either a new object, or an exported one modified in the notebook) into the plugin, call :py:meth:`~jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction.SpectralExtraction.import_extract`:

.. code-block:: python

  sp_ext.import_extract(ext)


.. note::

    Horne extraction uses uncertainties on the input 2D spectrum. If the
    spectrum uncertainties are not explicitly assigned a type, they are assumed
    to be standard deviation uncertainties. If no uncertainty is provided,
    it is assumed to be an array of ones.


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
    The line lists plugin is currently disabled if the 1D spectrum's x-axis is in pixels.

.. seealso::

    :ref:`Line Lists <line-lists>`
        Specviz documentation on Line Lists.


.. _specviz2d-line-analysis:

Line Analysis
=============

.. note::
    The line analysis plugin is currently disabled if the 1D spectrum's x-axis is in pixels.

.. seealso::

    :ref:`Line Analysis <line-analysis>`
        Specviz documentation on Line Analysis.

.. _specviz2d-export-plot:

Export
======

This plugin allows exporting the plot in a given viewer to various image formats.
