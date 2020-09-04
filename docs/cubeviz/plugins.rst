*********************
Data Analysis Plugins
*********************

Overview here...

Gaussian Smooth
===============

More words...

Collapse
===============

More words...

Model Fitting
=============

More words...

Contours
===============

More words...

Unit Conversion
===============

More words...

Line Lists
==========

More words...

Line Analysis
=============

More words...

How to Make Line and Continuum Maps
===================================

There are at least three ways to make a line map using
the one of three Cubeviz plugins: Collapse, Moment Maps, or Model
Fitting.  The first two methods currently require a data cube
that is already continuum-subtracted.  Continuum maps can be
created in a similar way using a cube that is not continuum
subtracted.

To make a line map using the Collapse plugin, first import a
continuum-subtracted data cube into Cubeviz.  Next, go to the Collapse
plugin and select the appropriate dataset using the
:guilabel:`Data` pulldown. Then set the :guilabel:`Axis` to 0
(wavelength axis) and the method to 'Mean' (or in the future when
it is available,'Sum').  Next either create and select a
:guilabel:`Region` in the spectrum viewer, or enter the lower and
upper spectral bounds manually.  When you :guilabel:`Apply` the
Collapse, a new collapsed 2D image of the line is created.
You can load this line map in any image viewer pane to inspect the
result.

A line map can also be created using the Moment Maps Plugin using a
similar workflow. Select the (continuum-subtracted) dataset in the
Plugin using the guilabel:`Data` pulldown.  Then either select a
region in the Spectral Region pulldown or enter the lower and upper
spectral bounds
