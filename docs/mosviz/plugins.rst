*********************
Data Analysis Plugins
*********************

.. include:: ../_templates/deprecated_config_banner.rst

The Mosviz data analysis plugins include operations on both
2D images and Spectrum one dimensional datasets.
Plugins that are specific to 1D spectra are described in
more detail under :ref:`Data Analysis Plugins <specviz-plugins>`. All plugins
are accessed via the plugin icon in the upper right corner of the Mosviz application.

.. _mosviz-metadata-viewer:

Metadata Viewer
===============

This plugin allows viewing of any metadata associated with the selected data.

If the data is loaded from multi-extension FITS that contains a primary header,
you will also see a :guilabel:`Show primary header` toggle. When enabled, the plugin will only
display the primary header metadata.

.. _mosviz-export-plot:

Export
======

This plugin allows exporting the plot and/or subsets in a given viewer to various formats.

.. _mosviz-plot-options:

Plot Options
============

This plugin gives access to per-viewer and per-layer plotting options.

.. seealso::

    :ref:`Image Plot Options <imviz-display-settings>`
        Documentation on Imviz display settings in the Jdaviz viewers.

.. seealso::

    :ref:`Spectral Plot Options <specviz-plot-settings>`
        Documentation on Specviz display settings in the Jdaviz viewers.

.. _mosviz-subset-plugin:

Subset Tools
============

.. seealso::

    :ref:`Subset Tools <imviz-subset-plugin>`
        Imviz documentation describing the concept of subsets in Jdaviz.

.. _mosviz-markers:

Markers
=======

.. seealso::

    :ref:`Markers <markers-plugin>`
        Imviz documentation describing the markers plugin.

Gaussian Smooth
===============

.. seealso::

    :ref:`Gaussian Smooth <gaussian-smooth>`
        Specviz documentation on gaussian smoothing of 1D spectra.

Model Fitting
=============

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

As in :ref:`Specviz <line-lists>`, the Line Lists Plugin includes a slider to adjust the redshift
or radial velocity.  In Mosviz, this is applied to the current row in the table
and is stored (and shown) in a column of the table.

.. warning::
    Using the redshift slider with many active spectral lines causes performance issues.
    If the shifting of spectral lines lag behind the slider, try plotting fewer lines.
    You can remove lines from the plot using, e.g., the "Erase All" button in the line lists UI.

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
`~specutils.Spectrum.meta` attribute of the :class:`~specutils.Spectrum` object
that is active in the 2D spectrum viewer.
