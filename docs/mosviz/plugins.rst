*********************
Data Analysis Plugins
*********************

The MOSviz data analysis plugins include operations on both
2D images and Spectrum1D one dimensional datasets.
Plugins that are specific to 1D spectra are described in
more detail under Specviz:Data Analysis Plugins.  All plugins
are accessed via the plugin icon in the upper right corner
of the MOSviz application.

Gaussian Smooth
===============

Gaussian smoothing of a spectrum is
described under Specviz:Data Analysis Plugins:Gaussian Smoothing.

.. seealso::

    `Gaussian Smooth <https://jdaviz.readthedocs.io/en/latest/specviz/plugins.html#gaussian-smooth>`_
        Specviz documentation on gaussian smoothing of 1D spectra.

Model Fitting
=============

The Model Fitting plugin is described in more detail by the
Specviz:Data Analysis Plugins:Model Fitting documentation.

.. seealso::

    `Model Fitting <https://jdaviz.readthedocs.io/en/latest/specviz/plugins.html#model-fitting>`_
        Specviz documentation on fitting spectral models.


Unit Conversion
===============

.. seealso::

    `Unit Conversion <https://jdaviz.readthedocs.io/en/latest/specviz/plugins.html#unit-conversion>`_
        Specviz documentation on unit conversion.


Line Lists
==========

.. seealso::

    `Line Lists <https://jdaviz.readthedocs.io/en/latest/specviz/plugins.html#line-lists>`_
        Specviz documentation on line lists.


Line Analysis
=============

.. seealso::

    `Line Analysis <https://jdaviz.readthedocs.io/en/latest/specviz/plugins.html#line-analysis>`_
        Specviz documentation on line analysis.



Slit Overlay
============

A slit can be added to the image viewer by opening the Slit Overlay plugin and clicking the :guilabel:`Apply` button.
The :guilabel:`Remove` button can be used to remove a slit once it has been applied to the image viewer.

In order to plot a slit onto the image viewer, we need WCS information from an image and slit position from a 2D spectrum.
WCS information is taken from the `meta` attribute of the :class:`~astropy.nddata.CCDData` object representing the data in the
image viewer. The slit position is calculated using the `S_REGION` header extension value, located in the `meta` attribute of
the :class:`~spectral_cube.SpectralCube` object that is active in the 2D spectrum viewer.
