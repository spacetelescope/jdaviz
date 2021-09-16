*********************
Data Analysis Plugins
*********************

The Mosviz data analysis plugins include operations on both
2D images and Spectrum1D one dimensional datasets.
Plugins that are specific to 1D spectra are described in
more detail under Specviz:Data Analysis Plugins.  All plugins
are accessed via the plugin icon in the upper right corner
of the Mosviz application.


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

Line Lists
==========

.. seealso::

    :ref:`Line Lists <line-lists>`
        Specviz documentation on line lists.

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
