*********************
Data Analysis Plugins
*********************

The Mosviz data analysis plugins include operations on both
2D images and Spectrum1D one dimensional datasets.
Plugins that are specific to 1D spectra are described in
more detail under Specviz:Data Analysis Plugins.  All plugins
are accessed via the plugin icon in the upper right corner
of the Mosviz application.

.. _mosviz-metadata-viewer:

Metadata Viewer
===============

This plugin allows viewing of any metadata associated with the selected data.

.. _mosviz-export-plot:

Export Plot
===========

This plugin allows exporting the plot in a given viewer to various image formats.

.. _mosviz-plot-options:

Plot Options
============

This plugin gives access to per-viewer and per-layer plotting options.

Gaussian Smooth
===============

Gaussian smoothing of a spectrum is
described under Specviz:Data Analysis Plugins:Gaussian Smoothing.

.. seealso::

    :ref:`Gaussian Smooth <gaussian-smooth>`
        Specviz documentation on gaussian smoothing of 1D spectra.

Model Fitting
=============

The Model Fitting plugin is described in more detail by the
Specviz:Data Analysis Plugins:Model Fitting documentation.

.. seealso::

    :ref:`Model Fitting <model-fitting>`
        Specviz documentation on fitting spectral models.

.. _mosviz-line-lists:

Line Lists
==========

.. seealso::

    :ref:`Line Lists <line-lists>`
        Specviz documentation on line lists.


Redshift Slider
---------------

.. warning::
    Using the redshift slider with many active spectral lines causes performance issues.
    If the shifting of spectral lines lag behind the slider, try plotting less lines.
    You can deselect lines using, e.g., the "Erase All" button in the line lists UI.

As in :ref:`Specviz <line-lists>`, the Line Lists Plugin includes a slider to adjust the redshift
or radial velocity.  In Mosviz, this is applied to the current row in the table
and is stored (and shown) in a column of the table.

.. seealso::

    :ref:`Setting Redshift/RV <mosviz-redshift>`
        Setting Redshift/RV from the Notebook in Mosviz.

Line Analysis
=============

.. seealso::

    :ref:`Line Analysis <line-analysis>`
        Specviz documentation on line analysis.

Slit Overlay
============

A slit can be added to the image viewer by opening the Slit Overlay plugin and clicking the :guilabel:`Apply` button.
The :guilabel:`Remove` button can be used to remove a slit once it has been applied to the image viewer.

In order to plot a slit onto the image viewer, we need WCS information from an image and slit position from a 2D spectrum.
The slit position is calculated using the ``S_REGION`` header extension value, located in the
`~specutils.Spectrum1D.meta` attribute of the :class:`~specutils.Spectrum1D` object
that is active in the 2D spectrum viewer.
