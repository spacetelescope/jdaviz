.. _imviz-display-images:

*****************
Displaying Images
*****************

Imviz uses image viewers to visualize data from supported formats.
Much of the functionality is available both from the application GUI and
from the Jupyter notebook using API calls.
The Toolbar below gives you several image display options.
Right-click will open a drop-down with access to different options for each button.

.. image:: ../img/toolbar.jpg
    :alt: Imviz Toolbar


Selecting Data Set
==================

If you have already imported data into Imviz, you can select and deselect data within a viewer.

.. seealso::

    :ref:`Selecting Data Set <cubeviz-selecting-data>`
        Documentation on selecting data sets in the Jdaviz viewers.

.. _imviz_cursor_info:

Cursor Information
==================

By moving your cursor along the image viewer, you will be able to see information on the
cursor's location in pixel space (X and Y), the RA and Dec at that point, and the value
of the data there. This information is displayed in the top bar of the UI, on the
middle-right side.

Home
====

This button will reset your zoom and panning to display the entire image.

.. _imviz_box_zoom:

Box Zoom and Linked Box Zoom
============================

Linked Box Zoom is an Imviz-specific feature that allows the user to zoom
images in multiple different viewers simultaneously, not unlike
:ref:`imviz_pan_zoom`.

Single-viewer Box Zoom is also available and is used in a similar way as in
other Jdaviz tools.

Right click on the Box Zoom button to access all options and then left click to
select the type of Box Zoom desired.

.. image:: img/imviz_linked_box_zoom.png
    :alt: Imviz Box Zoom and Linked Box Zoom

.. seealso::

    :ref:`Pan/Zoom <cubeviz-pan-zoom>`
        Documentation on using Pan/Zoom in the Jdaviz viewers.

.. _imviz_pan_zoom:

Pan/Zoom and Linked Pan/Zoom
============================

Linked Pan/Zoom is an Imviz-specific feature that allows the user to pan and zoom
images in multiple different viewers simultaneously. This works by matching images
based on the way they are linked together. Images are linked by pixels on load time,
but you can re-link them via WCS using :ref:`imviz-link-control`.

Single-viewer Pan/Zoom is also available and is used in a similar way as in 
other Jdaviz tools.

Right click on the Pan/Zoom button to access all options and then left click to
select the type of Pan/Zoom desired.

.. image:: img/imviz_linked_pan_zoom.png
    :alt: Imviz Pan/Zoom and Linked Pan/Zoom

When in either of these modes, clicking on the image will recenter the image to the
location under cursor.

.. seealso::

    :ref:`Pan/Zoom <cubeviz-pan-zoom>`
        Documentation on using Pan/Zoom in the Jdaviz viewers.

From the API, you can programmatically zoom in and out. Zoom level:

    * 1 - real-pixel-size
    * 2 - zoomed in by a factor of 2
    * 0.5 - zoomed out by a factor of 2
    * ``'fit'`` - zoomed to fit the whole image width into display

For example::

    viewer = imviz.default_viewer
    viewer.zoom_level
    viewer.zoom_level = 1  # Set the zoom level directly.
    viewer.zoom(2)  # Set the relative zoom based on current zoom level.

.. _imviz_defining_spatial_regions:

Defining Spatial Regions
========================

Spatial regions allow users to select subsets of the data array for use in
specific analysis functions in the plugin toolbar, for example in the
:ref:`aper-phot-simple` plugin.
Users can create spatial regions either in Imviz or the Jupyter notebook.

.. seealso::

    :ref:`Defining Spatial Regions <spatial-regions>`
        Documentation on defining spatial regions in an image viewer.

.. seealso::

    :ref:`Importing Spatial Regions <imviz-import-regions-api>`
        Importing spatial regions from within the Jupyter notebook.

You can :ref:`import regions from the AP I<imviz-import-regions-api>`.
You can also retrieve the results as `regions.Regions` as follows, assuming
``imviz`` is the instance of your Imviz application::

    regions = imviz.get_interactive_regions()
    regions

Blinking
========

Blinking is an Imviz-specific functionality that allows a user to quickly switch
between viewing two or more images, as long as they are linked (see :ref:`imviz_pan_zoom` for
more on linking behavior). This can be done by selecting the |icon-blink| icon and
then clicking on the image. You can also blink by pressing the "b" key on your
keyboard while moused over the image.

From within the Jupyter notebook::

    viewer = imviz.default_viewer
    viewer.blink_once()

Contrast/Bias
=============

In addition to changing :ref:`contrast` and :ref:`bias` in the :ref:`display-settings`,
Imviz has a |icon-white-to-black| button under the |icon-blink| menu that can also
adjust those values.

After right-clicking on the blink icon, left click on the constrast/bias icon to activate it.
Now you can click and drag on the image viewer to change to change the contrast
and bias. Moving along the X-axis will change the bias and moving along the Y-axis will change the
contrast. If you would like to reset to the default contrast and bias settings, you can
double-click on the display while the mode is active.

Display Settings
================

.. seealso::

    :ref:`Display Settings <display-settings>`
        Documentation on various display settings in the jdaviz viewers.

From within the Jupyter notebook::

    viewer = imviz.default_viewer
    viewer.cuts = '95%'
    viewer.colormap_options
    viewer.set_colormap('viridis')


Adding New Viewers
==================

In the toolbar towards the top of the UI, there is a |icon-plus| icon
that when clicked will add new viewers to the application. You can then select from the data
that has been loaded into the application to be visualized in these additional viewers.
You can then utilize some of the Imviz-specific features, like :ref:`imviz_pan_zoom`.

You can also open a new viewer from the API::

    viewer_2_name = 'Window 2'
    viewer_2 = imviz.create_image_viewer(viewer_name=viewer_2_name)
    imviz.app.add_data_to_viewer(viewer_2_name, 'MyImportedData')

where ``'MyImportedData'`` is a data set that has already been imported into Imviz.
