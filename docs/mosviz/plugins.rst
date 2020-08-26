*********************
Data Analysis Plugins
*********************

Overview here...

Gaussian Smooth
===============

More words...

Model Fitting 
=============

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

Slit Overlay
============

A slit can be added to the image viewer by opening the Slit Overlay plugin and clicking the :guilabel:`Apply` button.
The :guilabel:`Remove` button can be used to remove a slit once it has been applied to the image viewer.

In order to plot a slit onto the image viewer, we need WCS information from an image and slit position from a 2D spectrum. WCS information is taken from the `meta` attribute of the :class:`~astropy.nddata.CCDData` object representing the data in the image viewer. The slit position is calculated using the `S_REGION` header extension value, located in the `meta` attribute of the :class:`~spectral_cube.SpectralCube` object that is active in the 2D spectrum viewer.
