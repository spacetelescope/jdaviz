.. _plugins-spectral_extraction_2d:
.. rst-class:: section-icon-mdi-tune-variant

************************
2D Spectral Extraction
************************

.. plugin-availability::

Extract 1D spectra from 2D spectroscopic data.

Description
===========

The 2D Spectral Extraction plugin exposes `specreduce <https://specreduce.readthedocs.io>`_
methods for tracing, background subtraction, and spectral extraction from 2D spectra.

**Key Features:**

* Extract 1D from 2D spectra
* Configurable extraction aperture
* Background subtraction
* Trace following
* Uncertainty propagation

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

   sp_ext = jd.plugins['2D Spectral Extraction']
    sp_ext.trace_type = 'Polynomial'
    sp_ext.trace_order = 2
    sp_ext.trace_window = 10
    sp_ext.trace_peak_method = 'Gaussian'

To export and access the :py:class:`specreduce.tracing.Trace` object defined in the plugin,
call :py:meth:`~jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction.SpectralExtraction2D.export_trace`:

.. code-block:: python

    trace = sp_ext.export_trace()


Trace objects created outside of jdaviz can be loaded into the app
via ``load``:

.. code-block:: python

    jd.load(my_trace, data_label="my trace")

or directly into the plugin
via :py:meth:`~jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction.SpectralExtraction2D.import_trace`

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

Backgrounds can either be created around the trace defined in the earlier Trace section
or around a new, flat trace by selecting "Manual" in the Background Type dropdown.

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

To export and access the :py:class:`specreduce.background.Background` object defined in the plugin,
call :py:meth:`~jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction.SpectralExtraction2D.export_bg`:

.. code-block:: python

  bg = sp_ext.export_bg()

To access the background image, background spectrum, or background-subtracted image as a
:class:`~specutils.Spectrum` object,
call :py:meth:`~jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction.SpectralExtraction2D.export_bg_img`,
:py:meth:`~jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction.SpectralExtraction2D.export_bg_spectrum`,
or :py:meth:`~jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction.SpectralExtraction2D.export_bg_sub`, respectively.

To import the parameters from a :py:class:`specreduce.background.Background` object into the plugin,
whether it's new or was exported and modified in the notebook,
call :py:meth:`~jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction.SpectralExtraction2D.import_bg`:

.. code-block:: python

  sp_ext.import_bg(bg)

Extract
-------

The extraction step of the plugin extracts a 1D spectrum from an input 2D spectrum via
:py:mod:`specreduce.extract`.

Once you interact with any of the inputs in the extract step or hover over that area
of the plugin, the live visualization will change to show the center (dotted line) and
edges (solid lines) of the extraction region.

The input 2D spectrum defaults to "From Plugin", which will use the settings defined in the
Background step to create a background-subtracted image without needing to export it into the app
itself. To use a different 2D spectrum loaded in the app (or exported from the Background step),
choose that from the dropdown instead.  To skip background subtraction, choose the original 2D
spectrum as input.

To visualize or export the resulting 2D spectrum, provide a data label and click "Extract".
The resulting spectrum object can be :ref:`accessed from the API <specviz2d-export-data-1d>`
in the same way as any other data product in the spectrum viewer.

UI Access
=========

.. wireframe-demo::
   :demo: plugins,plugins@1000:open-panel
   :enable-only: plugins
   :plugin-name: 2D Spectral Extraction
   :demo-repeat: false

Click the :guilabel:`Spectral Extraction` icon in the plugin toolbar to:

1. Define extraction aperture
2. Set background regions
3. Configure extraction parameters
4. Extract 1D spectrum

API Access
==========

Extraction parameters can be set from the notebook by accessing the plugin.

.. code-block:: python

    plg = jd.plugins['Spectral Extraction']
    plg.aperture_width = 5  # pixels
    plg.ext_type = 'Boxcar'
    plg.ext_width = 8
    plg.extract()

To export and access
the :py:class:`~jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction.SpectralExtraction2D` object defined
in the plugin,
call :py:meth:`~jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction.SpectralExtraction2D.export_extract`:

.. code-block:: python

  ext = plg.export_extract()

To access the extracted spectrum as a :class:`~specutils.Spectrum` object,
call :py:meth:`~jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction.SpectralExtraction2D.export_extract_spectrum`.

To import the parameters from
a :py:class:`~jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction.SpectralExtraction2D` object
(either a new object, or an exported one modified in the notebook) into the plugin,
call :py:meth:`~jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction.SpectralExtraction2D.import_extract`:

.. code-block:: python

  sp_ext.import_extract(ext)


.. note::

    Horne extraction uses uncertainties on the input 2D spectrum. If the
    spectrum uncertainties are not explicitly assigned a type, they are assumed
    to be standard deviation uncertainties. If no uncertainty is provided,
    it is assumed to be an array of ones.

.. plugin-api-refs::
   :module: jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction
   :class: SpectralExtraction2D

See Also
========

* :ref:`specviz2d-plugins` - Specviz2d extraction documentation
