.. _viewers-spectrum_3d:
.. rst-class:: section-icon-mdi-plus-box

************
3D Spectrum
************

3D Spectrum viewers show data loaded with `format = 3D Spectrum`. 
Much of the functionality is available both from the application GUI and from the Jupyter notebook using API calls. 

Toolbar
=======

The Toolbar on the top right of the viewer gives you several imaging and spectroscopic
display options. Right click will open a dropdown with access to different options
for each button.

Home
--------------------
This button will reset your zoom and panning to display the entire image.

Previous zoom is also available by right-clicking on the home icon and selecting the previous zoom icon. 
This will revert to the last saved zoom state. Zoom states are saved when beginning a zoom selection or when 
activating a pan/zoom tool.

Box Zoom and Linked Box Zoom
----------------------------
Linked Box Zoom is enabled only when there are multiple viewers that allows the user to zoom cubes in 
multiple different viewers simultaneously. 

Single-viewer Box Zoom is also available and is used in a similar way as in other Jdaviz tools. 
To access this option when there are multiple viewers, right-click on the Linked Box Zoom button and 
left-click on the second option down to select it.

.. _image-pan-zoom:

Pan/Zoom and Linked Pan/Zoom
----------------------------

Pan/Zoom is found by right-clicking on the zoom icon, and left clicking the pan/linked pan button
Linked Pan/Zoom is enabled only when there are multiple viewers that
allows the user to pan and zoom images in multiple different viewers simultaneously. This works by matching cubes
based on the way they are linked together. 

Single-viewer Pan/Zoom is also available and is used in a similar way as in
other Jdaviz tools. To access this option when there are multiple viewers, right-click on the
Linked Pan/Zoom button and left-click on the second option down to select it.

When in either of these modes, clicking on the image will recenter the image to the
location under cursor.

Defining Spatial Regions
------------------------

Spatial regions allow users to select subsets of the data array for use in
specific analysis functions in the plugin toolbar, for example in the
:ref:`plugins-aperture_photometry` plugin.
Users can create spatial regions either in Jdaviz or the Jupyter notebook.
If a 1D Spectrum viewer has already been created, once a region is selected, 
the cube will be collapsed in wavelength space over the region, 
and the resulting spectrum will be displayed in the 1D spectrum viewer.

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

.. _3dspec-spectrum-at-spaxel:

Spectrum At Spaxel
------------------

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

Focus mode 
----------
Clicking on the focus mode button expands the viewer to fill the application.  
The right hand plugin feature is not accessible in the UI. Hovering over a pixel show the cursor information. 
Click on the Focus mode button again to exit. 

Clone Viewer
------------
Under the Focus mode button, there is a |icon-clone| button to clone the viewer. Clicking this button duplicates the viewer with the same
data and subsets with name: `Original Name[X]`, where `X` is the number of times the viewer has been cloned.

Detach Viewer 
-------------
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
   :steps-json: [{"action": "show-sidebar", "value": "loaders", "delay": 1500, "caption": "Open the data loader"}, {"action": "select-tab", "value": "Viewer", "delay": 1500, "caption": "Select the Viewer tab"}, {"action": "select-dropdown", "value": "Viewer Type:3D Spectrum", "delay": 1500, "caption": "Set viewer type to 3D Spectrum"}]