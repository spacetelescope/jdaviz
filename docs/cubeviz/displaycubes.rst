.. _cubeviz-display-cubes:

****************
Displaying Cubes
****************

.. include:: ../_templates/deprecated_config_banner.rst

The Cubeviz layout includes two image viewers (at the top of the app)
and one spectrum viewer (at the bottom of the app), which it attempts to
populate automatically when the first dataset is loaded. By default, Cubeviz
attempts to parse and display the flux in the top left viewer and the uncertainty
in the top right viewer. The spectrum
viewer is populated by default by collapsing the spatial axes using the "Sum"
function. The indicators that the load machinery looks for in each HDU to
populate the viewers are below (note that in all cases, header values are
converted to lower case):

    - Flux viewer: ``hdu.name`` is in the set ``['flux', 'sci']``
    - Uncertainty viewer: ``hdu.header.keys()`` includes "errtype" or ``hdu.name``
      is in the set ``['ivar', 'err', 'var', 'uncert']``
    - Loaded but not displayed: ``hdu.data.dtype`` is `int`, `numpy.uint` or `numpy.uint32`, or
      ``hdu.name`` is in the set ``['mask', 'dq']``

The next section describes how to manually select data in cases where a viewer
is not automatically populated or a user wants to change the data displayed.
Different statistics for collapsing the spectrum displayed in the spectrum
viewer can be chosen as described in
:ref:`Display Settings <imviz-display-settings>`. Note that any spatial subsets will
also be collapsed into a spectrum using the same statistic and displayed in
the spectrum viewer along with the spectrum resulting from collapsing all the
data in each spectral slice.

Much of the Cubeviz functionality can be handled within the tool or the
Jupyter notebook using an API. The Toolbar below gives you several spectroscopic
display options. Right click will open a dropdown with access to different options
for each button.

.. image:: ./img/cubeviztoolbar.png
    :alt: Cubeviz Toolbar

.. _cubeviz-selecting-data:

Selecting a Data Set
====================

If you have already imported data into Cubeviz, you can select and deselect data within a viewer.

.. seealso::

    :ref:`Selecting a Data Set <imviz-selecting-data>`
        Documentation on selecting data sets in the Jdaviz viewers.

Home
====

This button will reset your zoom and panning to display the entire image.

.. _cubeviz-box-zoom:

Box Zoom and Linked Box Zoom
============================

.. seealso::

    :ref:`Box Zoom and Linked Box Zoom in Imviz <imviz-box-zoom>`
        Documentation on panning and zooming in Imviz.

.. _cubeviz-pan-zoom:

Pan/Zoom and Linked Pan/Zoom
============================

.. seealso::

    :ref:`Pan/Zoom and Linked Pan/Zoom in Imviz <imviz-pan-zoom>`
        Documentation on panning and zooming in Imviz.

.. note:: Pan/Zoom API and click-to-center feature in Imviz is not yet available on Cubeviz.

.. _cubeviz-defining-spatial-regions:

Defining Spatial Regions
========================

.. seealso::

    :ref:`Defining Spatial Regions <imviz-defining-spatial-regions>`
        Documentation on defining spatial regions in an image viewer.

Spatial regions allow users to select subsets of the data array for
specific analysis function in the plugin toolbar. Users can create spatial regions either in Cubeviz or
the Jupyter notebook. Once a region is selected, the cube will be collapsed in wavelength space
over the region, and the resulting spectrum will be displayed in the 1D spectrum viewer at
the bottom of the UI.

.. image:: img/subset_creation.png
    :alt: Subset creation in Cubeviz

.. _cubeviz-spectrum-at-spaxel:

Spectrum At Spaxel
==================

This tool allows the user to create a single-spaxel subset in an image viewer. This subset will then be
visualized in the spectrum viewer by showing the spectrum at that spaxel.
While this tool is active, hovering over a pixel in the image viewer will show a preview of the spectrum
at that spaxel in the spectrum viewer, and left-clicking will create a new subset at that spaxel.
Click again to move the region to a new location under the cursor. Holding down the
alt key (Alt key on Windows, Option key on Mac) while clicking on a spaxel creates a new subset at
that point instead of moving the previously created region.
You can then compare spectra at different spaxels using the spectrum viewer.
You can also use the subset modes that are explained in the
:ref:`Spatial Regions <imviz-defining-spatial-regions>`
section above in the same way you would with the other subset selection tools.

Note that moving the cursor outside of the image viewer or deactivating the spectrum-at-spaxel tool
will revert the spectrum viewer zoom limits from the zoomed-in preview view to the limits set prior
to using the tool. Thus it may be necessary to reset the zoom to see any single-spaxel subset spectra
created using the tool.

.. _cubeviz-display-settings:

Display Settings
================

.. seealso::

    :ref:`Display Settings <imviz-display-settings>`
        Documentation on various display settings in the jdaviz viewers.
