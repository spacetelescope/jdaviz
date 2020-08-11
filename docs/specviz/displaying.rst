******************
Displaying Spectra
******************

Words go here



Selecting Data Set
==================

More words...

Pan/Zoom
========

More words...

Defining Spectral Regions
=========================

Spectral regions can be defined by clicking on the "hammer and screwdriver" icon at the top left of an image
viewer. Then, click the "region" icon to set the cursor dragging function in "spectral region selection" mode.

.. image:: img/spectral_region_1.png

Now, you can move the mouse to one of the end points (in wavelength) of the region you want to select, and drag
it to the other end point. The selected region background will display in light gray color, and the spectral trace
in dark red.

You also see in the top tool bar that the region was added to the data hold, and is named "Subset 1".

.. image:: img/spectral_region_2.png

Clicking on that selector, you can add more regions by selecting the "create new" entry:

.. image:: img/spectral_region_3.png

Now just select the end points of the new region as before. It will be added to the data hold with name "Subset 2":

.. image:: img/spectral_region_4.png

In a notebook cell, you can access the regions using the `get_spectral_regions()` function:

.. image:: img/spectral_region_5.png


Plot Settings
=============

More words...