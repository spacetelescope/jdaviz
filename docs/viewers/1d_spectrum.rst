.. _viewers-spectrum_1d:
.. rst-class:: section-icon-mdi-plus-box

************
1D Spectrum
************

1D Spectrum viewers show data loaded with

- `format = 1D Spectrum`,
- `format = 2D Spectrum` if the `Extract 1D Spectrum` toggle is set to ON, 
- `format = 3D Spectrum` if the `Extract 1D Spectrum` toggle is set to ON, 

Much of the functionality is available both from the application GUI and from the Jupyter notebook using API calls. 

The first spectrum you load will be automatically displayed in the viewer with
the view window set by the extent of the spectrum. Additional spectra may not be
fully shown if they exceed the bounds of the plotted area, which are set based
on the first displayed spectrum. The bounds can be changed via the
:ref:`Pan/Zoom <1dspectrum-pan-zoom>` tool or by deselecting the current spectra and
selecting a different spectrum for display.

Toolbar
=======

The Toolbar on the top right of the viewer gives you several spectroscopic
display options. Right click will open a dropdown with access to different options
for each button.

Home and Linked Home
--------------------
This button will reset your zoom and panning to display the entire image.

Linked Home is enabled only when there are multiple viewers that allows the user to reset in 
multiple different viewers simultaneously. 

Previous zoom is also available by right-clicking on the home icon and selecting the previous zoom icon. 
This will revert to the last saved zoom state. Zoom states are saved when beginning a zoom selection or when 
activating a pan/zoom tool.

Zoom and Linked Zoom
----------------------------
Linked Zoom is enabled only when there are multiple viewers that allows the user to zoom images in 
multiple different viewers simultaneously. 

Single-viewer Zoom is also available and is used in a similar way as in other Jdaviz tools. 
To access this option when there are multiple viewers, right-click on the Linked Box Zoom button and 
left-click on the second option down to select it.

The |icon-box-zoom| (box),  |icon-xrange-zoom| (x-range), and |icon-yrange-zoom| zoom tools allow you to zoom by
clicking and dragging with your mouse. The box zoom tool adjusts both the x and y range of
the plot, the x-range tool zooms only the x-axis to the selected region, and y-range tool zooms only the y-axis to the selected range. 
While clicking and dragging you will see the selected region as a red box. 

You can switch between the different zoom tools by right-clicking
(or your trackpad equivalent) on the currently selected zoom icon on the viewer
toolbar, which will open a menu of choices as in the screenshot below.

.. _image-pan-zoom:

Pan/Zoom and Linked Pan/Zoom
----------------------------

Linked Pan/Zoom is enabled only when there are multiple viewers that
allows the user to pan and zoom images in multiple different viewers simultaneously. This works by matching images
based on the way they are linked together. For 2D and 1D Spectrum viewers, these are linked by the spectral axis. 

Single-viewer Pan/Zoom is also available and is used in a similar way as in
other Jdaviz tools. To access this option when there are multiple viewers, right-click on the
Linked Pan/Zoom button and left-click on the second option down to select it.

There are several ways to pan around a spectrum or zoom in on features of
interest. Right click will open a dropdown with access to different
options described below.

2D Bidirectional Pan/Zoom
^^^^^^^^^^^^^^^^^^^^^^^^^

The |icon-zoom-pan-2d| icon allows you to zoom using the scroll wheel.
The window will zoom into the area around your cursor.
To pan, simply click and drag the window.

Horizontal/Vertical Zoom
^^^^^^^^^^^^^^^^^^^^^^^^
The |icon-zoom-pan-horiz| (Horizontal) and |icon-zoom-pan-vert| (Vertical) Zoom tools allow you to zoom along each axis,
while locking the other.  You can also zoom by scrolling.

Range Selection
===============

This button will allow you to create a spectral region. Spectral regions allow users to 
select subsets of the spectral array for use in
specific analysis functions in the plugin toolbar, for example in the
:ref:`plugins-model-fitting` plugin.
Users can create spectral regions either in Jdaviz or the Jupyter notebook.

Regions can be created by first clicking the |icon-region-spec| icon
then clicking and dragging (using the mouse) until the
desired spectral region, after which you release the mouse button. 
The selected region will display in color, and coded to subset number and listed under the subsets dropdown.

There are other options available for region of interest. Clicking on the data menu, select the region of interest, 
and then select `EDIT SUBSET` on the bottom right of the data menu. Several options will pop up.  
* ``Resize in Viewer`` allows you to resize the subset directly in the viewer by dragging the sides of the region.
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
location in pixel space (X and Y), the wavelength value at that point, and the value of the data there. 
This information is displayed in the top bar of the UI, on the middle-left side.

By default, the cursor information will correspond to the top spectral layer in the viewer. 
To change to a specific data-layer, click the layer-icon in the top bar to cycle between “auto”, “cursor”, or specific data layers.


UI Access
=========

.. guidestar-demo:: _static/jdaviz-wireframe.html
   :repeat: false
   :init-steps-json: [{"action":"disable-toolbar-except","value":"loaders"}]
   :steps-json: [{"action": "show-sidebar", "value": "loaders", "delay": 1500, "caption": "Open the data loader"}, {"action": "select-tab", "value": "Viewer", "delay": 1500, "caption": "Select the Viewer tab"}, {"action": "select-dropdown", "value": "Viewer Type:1D Spectrum", "delay": 1500, "caption": "Set viewer type to 1D Spectrum"}]