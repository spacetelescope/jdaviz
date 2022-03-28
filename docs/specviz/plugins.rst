.. _specviz-plugins:

*********************
Data Analysis Plugins
*********************

To enable quick analysis of astronomical spectra, Specviz ships with a number of
plugins that let you do various standard spectral analysis tasks.  Note that
these plugins all depend on ``specutils`` to do the actual analysis work - when
doing these operations in the Notebook you are often better off using
the ``specutils`` or ``astropy`` APIs directly instead of using the plugins. But
for quick-look or interaction heavy workflows, the plugins provide a UI-based
alternative.

Data analysis plugins are found in the plugin tray, accessed via the
:guilabel:`plugin` icon in the upper right corner of the Specviz application window.
Each plugin may be used to perform data analysis tasks on
selected datasets.

Input/Output
============

Data to be operated on are selected in each plugin via a
:guilabel:`Data` pulldown menu.

.. _specviz-metadata-viewer:

Metadata Viewer
===============

This plugin allows viewing of any metadata associated with the selected data.

.. _specviz-export-plot:

Export Plot
===========

This plugin allows exporting the plot in a given viewer to various image formats.

.. _specviz-plot-options:

Plot Options
============

This plugin gives access to per-viewer and per-layer plotting options.

Included in this plugin is a toggle called :guilabel:`Plot Uncertainty`,
which will show uncertainty values as a shaded area above and below the
spectrum. With this option toggled on, all spectra added to Specviz will
have their uncertainty values displayed as well.

.. _gaussian-smooth:

Gaussian Smooth
===============

.. image:: ../img/gaussian_smooth.png

Gaussian Smooth is performed on a Spectrum1D data object.
The spectrum is convolved with a Gaussian function.
The Gaussian standard deviation in pixels must be entered into the
:guilabel:`Standard deviation` field in the plugin.

A new Spectrum1D object is generated and is added to the spectrum
viewer.
It can be selected and shown in the viewer via the
:guilabel:`Data` icon in the viewer toolbar.

.. _specviz-model-fitting:

Model Fitting
=============

.. image:: ../img/model_fitting_components.png

Astropy models can be fit to a spectrum via the Model Fitting plugin.
Model components are selected via the :guilabel:`Model` pulldown menu.
Each component should be given a :guilabel:`Model ID`.
The :guilabel:`Add Model` button adds a Model Parameters block.

Model Parameters are automatically initialized with a guess.
These starting values can be edited by the user.
They may also be fixed by selecting the :guilabel:`Fixed?` checkbox,
so that they are not fit or changed by the model fitting.

A mathematical expression must be entered into the
:guilabel:`Model Equation Editor` to specify the mathematical
combination of models.
This is also necessary even if there is only one model component.
The model components are specified by their :guilabel:`Model ID`.
For example, add together Constant and Gaussian models with
model IDs 'C' and 'G1' by entering the Model Equation 'C+G1'.

Fitted models can be extracted from the app into notebook cells by using
the :meth:`~jdaviz.core.helpers.ConfigHelper.get_models` method of the
configuration helper class, e.g.::

    specviz.get_models(model_label="Model")

The :meth:`~jdaviz.core.helpers.ConfigHelper.get_models` method returns the
fitted ``astropy`` model objects. If only
the parameters of the model are needed, those can be extracted using the
following code::

    specviz.get_model_parameters(model_label="Model")

If nothing is specified for the ``model_label`` keyword, information for
all models will be returned.

.. _unit-conversion:

Unit Conversion
===============

The spectral flux density and spectral axis units can be converted
using the Unit Conversion plugin.  The Spectrum1D object to be
converted is the currently selected spectrum in the spectrum viewer :guilabel:`Data`
icon in the viewer toolbar.

Select the frequency, wavelength, or energy unit in the
:guilabel:`New Spectral Axis Unit` pulldown
(e.g. Angstrom, Hertz, erg).

Select the flux density unit in the :guilabel:`New Flux Unit` pulldown
(e.g. Jansky, W/(Hz/m2), ph/(Angstrom cm2 s)).

The :guilabel:`Apply` button will convert the flux density and/or
spectral axis units and create a new Spectrum1D object that
is automatically switched to in the spectrum viewer.
The name of the new Spectrum1D object is "_units_copy_" plus
the flux and spectral units of the spectrum.

.. _line-lists:

Line Lists
==========

.. image:: ../img/line_lists.png

Line wavelengths can be plotted in the spectrum viewer using
the Line Lists plugin.

Line lists (e.g. Common Stellar, SDSS, CO) can be selected from
Preset Line Lists via the :guilabel:`Available Line Lists`
pulldown.
They are loaded and displayed by pressing :guilabel:`Load List`.
Each loaded list is shown under :guilabel:`Loaded Lines`.
Loaded line lists may be removed by pressing the
:guilabel:`circled-x` button.

The Loaded Lines include a :guilabel:`Custom` line list which is
automatically created, but populated with no lines.
Lines may be added to the Custom line list by entering
:guilabel:`Line Name`, :guilabel:`Rest Value`, and :guilabel:`Unit`
for the spectral axis and pressing :guilabel:`Add Line`.
Selected lines may be hidden by deselecting the associated check box.

The color of each line list may be adjusted with the color and
saturation sliders.
Entire line lists may be hidden in the display via
:guilabel:`Show All` and :guilabel:`Hide All`, located at the
bottom of each list.
Similarly, all of the line lists may be shown or hidden via
:guilabel:`Plot All` and :guilabel:`Erase All`, located at the
bottom of the plugin.

Redshift Slider
---------------

.. warning::
    Using the redshift slider with many active spectral lines causes performance issues.
    If the shifting of spectral lines lag behind the slider, try plotting less lines.
    You can deselect lines using, e.g., the "Erase All" button in the line lists UI.

The plugin also contains a redshift slider which shifts all of the plotted
lines according to the provided redshift/RV.  The slider applies a delta-redshift,
snaps back to the center when releasing, and has limits that default based
on the x-limits of the spectrum viewer.  This provides a convenient method
to fine-tune the position of the redshifted lines to the observed lines in 
the spectrum.

.. seealso::

    :ref:`Setting Redshift/RV <specviz-redshift>`
        Setting Redshift/RV from the Notebook.

.. _line-analysis:

Line Analysis
=============

The Line Analysis plugin returns statistics for a single spectral line.
The line is selected via the :guilabel:`region` tool in
the spectrum viewer to select a spectral subset. Note that you can have
multiple subsets in Specviz, but the plugin will only show statistics for the
selected subset.

A linear continuum is fitted and subtracted (divided for the case of equivalenth width) before
computing the line statistics.  By default, the continuum is fitted to a region surrounding 
the select line.  The width of this region can be adjusted, with a visual indicator shown
in the spectrum plot while the plugin is open.  The thick line shows the linear fit which
is then interpolated into the line region as shown by a thin line.  Alternatively, a custom
secondary region can be created and selected as the region to fit the linear continuum.

The statistics returned include the line centroid, gaussian sigma width, gaussian FWHM,
total flux, and equivalent width.

Redshift from Centroid
----------------------

Following the table of statistics, the centroid can be used to set the redshift by assigning
the centroid value to a line added in the :ref:`Line List Plugin <line-lists>`.  Select the
corresponding line from the dropdown, or by locking the selection to the identified line and
using the |icon-line-select| (line selector) tool in the spectrum viewer.
