.. _viewers-image:
.. rst-class:: section-icon-mdi-plus-box

*****
Image
*****

Image viewers show data loaded with `format = Image`. 
Much of the functionality is available both from the application GUI and from the Jupyter notebook using API calls. 

Toolbar
=======

On the top right of the viewer is the toolbar, which provides you with several image display options. 
Right-click or clicking on the bottom right of the button will open a dropdown with access to different options for each button.

The primary buttons:

Home and Linked Home
--------------------
This button will reset your zoom and panning to display the entire image.

Linked Home is enabled only when there are multiple viewers that allows the user to reset in 
multiple different viewers simultaneously. 

Previous zoom is also available by right-clicking on the home icon and selecting the previous zoom icon. 
This will revert to the last saved zoom state. Zoom states are saved when beginning a zoom selection or when 
activating a pan/zoom tool.

Box Zoom and Linked Box Zoom
----------------------------
Linked Box Zoom is enabled only when there are multiple viewers that allows the user to zoom images in 
multiple different viewers simultaneously. 

Single-viewer Box Zoom is also available and is used in a similar way as in other Jdaviz tools. 
To access this option when there are multiple viewers, right-click on the Linked Box Zoom button and 
left-click on the second option down to select it.

.. _image-pan-zoom:

Pan/Zoom and Linked Pan/Zoom
----------------------------
Linked Pan/Zoom is enabled only when there are multiple viewers that
allows the user to pan and zoom images in multiple different viewers simultaneously. This works by matching images
based on the way they are linked together. Images are linked by pixels on load time,
but you can re-link them via WCS using :ref:`plugins-orientation`.

Single-viewer Pan/Zoom is also available and is used in a similar way as in
other Jdaviz tools. To access this option when there are multiple viewers, right-click on the
Linked Pan/Zoom button and left-click on the second option down to select it.

When in either of these modes, clicking on the image will recenter the image to the
location under cursor.

From the API
~~~~~~~~~~~~

From the API, you can programmatically zoom in and out. Zoom level:

    * 1 - real-pixel-size
    * 2 - zoomed in by a factor of 2
    * 0.5 - zoomed out by a factor of 2
    * ``'fit'`` - zoomed to fit the whole image width into display

For example:

.. code-block:: python

    viewer = imviz.default_viewer
    viewer.zoom_level
    viewer.zoom_level = 1  # Set the zoom level directly.
    viewer.zoom(2)  # Set the relative zoom based on current zoom level.


Defining Spatial Regions
------------------------

Spatial regions allow users to select subsets of the data array for use in
specific analysis functions in the plugin toolbar, for example in the
:ref:`plugins-aperture_photometry` plugin.
Users can create spatial regions either in Jdaviz or the Jupyter notebook.

Regions can be created by first clicking the |icon-region-circ| icon (to draw a circular region),
then clicking and dragging (using the mouse) until the
desired region is covered by a colored shape, after which you release the mouse button.
If you want to draw other shapes, right click on the icon to see a dropdown of supported shapes
and left click on it to choose the shape, then draw as mentioned above.

Once you have completed the action of clicking and dragging, there is an opportunity to reposition
the region of interest by clicking on it and moving the region to a different location in the image viewer.
If you are satisfied with the positioning of your region of interest, simply click another part of the
viewer to lock it in place.

There are other options available for region of interest. Clicking on the data menu, select the region of interest, 
and then select `EDIT SUBSET` on the bottom right of the data menu. Several options will pop up.  
* ``Resize in Viewer`` allows you to resize the subset directly in the viewer by dragging the white boxes on the corners.
* ``Edit in plugin`` opens up the Subset tools plugin. 
Below are several options: 

* ``replace``: will remove the previously created selection and place the newly created subset.
* ``or``: allows you to create another subset that extends the existing subset.
* ``and``: only leaves behind the overlapping region between the existing subset and any additional subsets.
* ``xor``: only leaves behind the non-overlapping region between the existing subset and any additional subsets.
* ``andnot``: will de-select any parts of the existing subset that overlaps with any additional subsets.

You can use these options to further adjust the region of interest and adapt it to your use case.

.. seealso::
    :ref:`Subsets & Regions <subsets>`
        Create and manage spatial and spectral subsets of your data.

.. seealso::
    :ref:`Exporting Spatial Regions <export-subsets>`
        Exporting regions from within the Jupyter notebook.

.. seealso::
    `Defining subsets using glue <http://docs.glueviz.org/en/stable/getting_started/#defining-subsets>`_
        Glueviz documentation on defining and refining subsets. Slightly different UI but same approach.

There are options available in the `Plotting Option <settings-plot_options>` 
to make subsets visible or invisible, to change their color, and to change their opacity.


Blinking
--------

Blinking allows a user to quickly switch
between viewing two or more images, as long as they are linked (see :ref:`image-pan-zoom` for
more on linking behavior). This can be done by selecting the |icon-blink| icon (only available if
there are more than one image loaded in the viewer) and then left-clicking on the image to blink
forward; right-clicking to blink backwards.

You can also blink forward by pressing the "b" key on your keyboard while moused over the image.
If you press Shift + "b" ("B"), you may blink backwards.

From the API
~~~~~~~~~~~~

From the API within the Jupyter notebook:

.. code-block:: python

    viewer = jdaviz.viewers['Image']
    viewer.blink_once()

And to blink backwards:

.. code-block:: python

    viewer.blink_once(reversed=True)

Contrast/Bias
=============

In addition to changing :ref:`contrast` and :ref:`bias` in the :ref:`settings-plot_options`,
the Image viewer has a |icon-white-to-black| button under the |icon-blink| menu that can also
adjust those values.

After right-clicking on the blink icon, left click on the constrast/bias icon to activate it.
Now you can click and drag on the image viewer to change the contrast
and bias. Moving along the X-axis will change the bias and moving along the Y-axis will change the
contrast. If you would like to reset to the default contrast and bias settings, you can
double-click on the display while the mode is active.

Colormap
========

In addition to changing :ref:`contrast` and :ref:`bias` in the :ref:`settings-plot_options`,
the Image viewer has a |icon-cmap| button under the |icon-blink| menu that can also
adjust those values.

After right-clicking on the blink icon, left click on the colormap icon to activate it.
Now you can change the colormap on the toolbar by clicking the dropdown and selecting your colormap. 
Click the `x` next to `COLORMAP` to leave this feature. 

Stretch
=======

In addition to changing :ref:`stretch` in the :ref:`settings-plot_options`,
the Image viewer has a |icon-stretch| button under the |icon-blink| menu that can also
adjust those values.

After right-clicking on the blink icon, left click on the stretch icon to activate it.
Now you can change the stretch on the toolbar by clicking on the dropdown and selecting your stretch. 
Click the `x` next to `STRETCH` to leave this feature. For fine tuning the min/max values, see :ref:`settings-plot_options`. 

Opacity
=======

In addition to changing :ref:`opacity` in the :ref:`settings-plot_options`,
the Image viewer has a |icon-opacity| button under the |icon-blink| menu that can also
adjust those values.

After right-clicking on the blink icon, left click on the opacity icon to activate it.  
Now you can change the opacity in the toolbar by dragging the bar.  The number on the right is the opacity between 0 (transparent) and 1 (opaque). 
Click the `x` next to `OPACITY` to leave this feature. 


Focus mode 
==========
Clicking on the focus mode button expands the viewer to fill the application.  
The right hand plugin feature is not accessible in the UI. Hovering over a pixel show the cursor information. 
Click on the Focus mode button again to exit. 

Clone Viewer
===========
Under the Focus mode button, there is a |icon-clone| button to clone the viewer. Clicking this button duplicates the viewer with the same
data and subsets with name: `Original Name[X]`, where `X` is the number of times the viewer has been cloned.

Detach Viewer 
=============
Under the Focus mode button, there is a |icon-detach| button to detach the viewer from the app. Clicking this button 
opens a new window which displays the viewer of choice.  Use your computer's native exit button to delete the viewer.
Note: anything you do in this viewer is replicated in the main application, and deleting this viewer does **not** delete the viewer in the main application.

If nothing appears, check that popups are allowed on your browser. 


Cursor Information
==================
By moving your cursor along the image viewer, you will be able to see information on the cursor's 
location in pixel space (X and Y), the RA and Dec at that point, and the value of the data there. 
This information is displayed in the top bar of the UI, on the middle-left side.

By default, the cursor information will correspond to the top image layer in the viewer. 
To change to a specific data-layer, click the layer-icon in the top bar to cycle between “auto”, “cursor”, or specific data layers.


UI Access
=========

.. guidestar-demo:: _static/jdaviz-wireframe.html
   :repeat: false
   :init-steps-json: [{"action":"disable-toolbar-except","value":"loaders"}]
   :steps-json: [{"action": "show-sidebar", "value": "loaders", "delay": 1500, "caption": "Open the data loader"}, {"action": "select-tab", "value": "Viewer", "delay": 1500, "caption": "Select the Viewer tab"}, {"action": "select-dropdown", "value": "Viewer Type:Image", "delay": 1500, "caption": "Set viewer type to Image"}]


Notes on GWCS
-------------

If your *reference data* has GWCS with a bounding box, any coordinates transformation
outside that bounding box is less reliable. This still applies even when you are
looking at some other data that is not the reference data if they are linked by WCS
because all transformations in ``glue`` go through the reference data. Such a situation
is indicated by the affected coordinates becoming gray.

If your data of interest also has a GWCS with a bounding box, only
the mouseover data inside the bounding box is completely reliable.
Unreliable coordinates transformation here
will also be hidden or grayed out in a similar fashion as above.

To avoid inaccurate transforms, consider one of the following workflows:

* Make sure your reference data's GWCS has a bounding box that encompasses all
  the other data you are trying to visualize together.
* If the above is not possible, avoid overlaying different data with GWCS that
  do not overlap.

.. warning::

    If you rely on the GWCS bounding box, it will be set to ``None`` when
    you data is loaded into Imviz, but the original bounding box,
    if available, is now in a hidden ``_orig_bounding_box``
    attribute of the GWCS object. You can restore the bounding box by
    assigning the value of ``_orig_bounding_box`` back to its
    ``bounding_box`` attribute.

Note that FITS WCS has no similar concept of bounding box.