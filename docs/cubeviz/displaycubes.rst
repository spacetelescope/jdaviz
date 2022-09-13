.. _cubeviz-display-cubes:

****************
Displaying Cubes
****************

The Cubeviz layout includes three image viewers (at the top of the app)
and one spectrum viewer (at the bottom of the app), which it attempts to
populate automatically when the first dataset is loaded. By default, Cubeviz
attempts to parse and display the flux in the top left viewer, the uncertainty
in the top middle viewer, and the mask into the top right viewer. The spectrum
viewer is populated by default by collapsing the spatial axes using the `max`
function. The indicators that the load machinery looks for in each HDU to
populate the viewers are below (note that in all cases, header values are
converted to lower case):

    - Flux viewer: ``hdu.name`` is in the set ``['flux', 'sci']``
    - Uncertainty viewer: ``hdu.header.keys()`` includes "errtype" or ``hdu.name``
      is in the set ``['ivar', 'err', 'var', 'uncert']``
    - Mask viewer: ``hdu.data.dtype`` is `int`, `numpy.uint` or `numpy.uint32`, or
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

.. image:: ./img/cubeviztoolbar.jpg
    :alt: Speciz Toolbar

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

    :ref:`Box Zoom and Linked Box Zoom in Imviz <imviz_box_zoom>`
        Documentation on panning and zooming in Imviz.

.. _cubeviz-pan-zoom:

Pan/Zoom and Linked Pan/Zoom
============================

.. seealso::

    :ref:`Pan/Zoom and Linked Pan/Zoom in Imviz <imviz_pan_zoom>`
        Documentation on panning and zooming in Imviz.

.. note:: Pan/Zoom API and click-to-center feature in Imviz is not yet available on Cubeviz.

.. _cubeviz_defining_spatial_regions:

Defining Spatial Regions
========================

.. seealso::

    :ref:`Defining Spatial Regions <imviz_defining_spatial_regions>`
        Documentation on defining spatial regions in an image viewer.

Spatial regions allow users to select subsets of the data array for
specific analysis function in the plugin toolbar. Users can create spatial regions either in Cubeviz or
the Jupyter notebook. Once a region is selected, the cube will be collapsed in wavelength space
over the region, and the resulting spectrum will be displayed in the 1D spectrum viewer at
the bottom of the UI.

.. image:: img/subset_creation.png

.. _cubeviz-spectrum-at-spaxel:

Spectrum At Spaxel
==================

This tool allows the user to create a one spaxel subset in an image viewer. This subset will then be
visualized in the spectrum viewer by showing the spectrum at that spaxel. Users can hold down the
alt key (Alt key on Windows, Option key on Mac) while clicking on a spaxel to create a new subset at
that point. Users can then compare spectra at different spaxels using the spectrum viewer. Users can
also utilize the different subset modes that are explained in the
:ref:`Spatial Regions <imviz_defining_spatial_regions>` section.

.. _cubeviz-display-settings:

Display Settings
================

.. seealso::

    :ref:`Display Settings <imviz-display-settings>`
        Documentation on various display settings in the jdaviz viewers.

To access all of the different display settings for an image viewer, click the
|icon-settings-sliders| icon in the viewer toolbar or open the :ref:`Plot Options <cubeviz-plot-options>` plugin.
Changing the display settings **does not** change the underlying data, only the
visualization of that data.
