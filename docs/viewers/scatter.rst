.. _viewers-scatter:
.. rst-class:: section-icon-mdi-plus-box

*******
Scatter
*******

Scatter viewers show data loaded with

- ``format = Source Catalog``
- ``format = Generic Catalog``

Much of the functionality is available both from the application GUI and from the Jupyter notebook using API calls. 

Toolbar
=======

The Toolbar on the top right of the viewer gives you several scatter
display options. Right click will open a dropdown with access to different options
for each button.

Home
----
This |icon-home|  button will reset your zoom and panning to display the entire image.

Previous zoom is also available by right-clicking on the home icon and selecting the previous zoom icon. 
This will revert to the last saved zoom state. Zoom states are saved when beginning a zoom selection or when 
activating a pan/zoom tool.

.. _viewers-scatter-toolbar-zoom:

Zoom
----
Click on the |icon-box-zoom| icon to select zoom. The |icon-box-zoom| (box),  |icon-xrange-zoom| (x-range), and |icon-yrange-zoom| zoom tools allow you to zoom by
clicking and dragging with your mouse. The box zoom tool adjusts both the x and y range of
the plot, the x-range tool zooms only the x-axis to the selected region, and y-range tool zooms only the y-axis to the selected range. 
While clicking and dragging you will see the selected region as a red box. 

You can switch between the different zoom tools by right-clicking
(or your trackpad equivalent) on the currently selected zoom icon on the viewer
toolbar, which will open a menu of choices as in the screenshot below.

.. _viewers-scatter-toolbar-pan-zoom:

Pan/Zoom
--------

Select the |icon-zoom-pan-2d| to select pan/zoom. There are several ways to pan around a spectrum or zoom in on features of
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

.. _viewers-scatter-toolbar-range:

Range Selection
---------------

This |icon-region-spec| button will allow you to select a range of x-values. Regions allow users to 
select subsets of the scatter data for use in
specific analysis functions in the plugin toolbar. 
Users can create regions either in Jdaviz or the Jupyter notebook.

Regions can be created by first clicking the |icon-region-spec| icon
then clicking and dragging (using the mouse) until the
desired region, after which you release the mouse button. 
The selected region will display in color, and coded to subset number and listed under the subsets dropdown.

Right click will open a dropdown with access to different types of subset create: 
select points based on the y-range and rectangular subsets.

.. seealso::

    * :ref:`Edit subsets in Data Menu <data_menu-edit_subsets>`
        Edit subsets directly in the viewer from the ``data menu``  
    * :ref:`Subsets & Regions <subsets>`
        Create and manage spatial and spectral subsets of your data.
    * :ref:`Exporting Spatial Regions <export-subsets>`
        Exporting regions from within the Jupyter notebook.
    * `Defining subsets using glue <http://docs.glueviz.org/en/stable/getting_started/#defining-subsets>`_
        Glueviz documentation on defining and refining subsets. Slightly different UI but same approach.

There are options available in the :ref:`Plotting Option <settings-plot_options>` 
to make subsets visible or invisible, to change their color, and to change their opacity.


.. _viewers-scatter-toolbar-focusmode:

Focus mode 
----------
Clicking on the |icon-focus| focus mode button expands the viewer to fill the application.  
The right hand plugin feature is not accessible in the UI. Hovering over a pixel show the cursor information. 
Click on the |icon-focus-exit| focus mode exit button to exit. 

.. _viewers-scatter-toolbar-clone:

Clone Viewer
------------
Under the Focus mode button, there is a |icon-clone| button to clone the viewer. Clicking this button duplicates the viewer with the same
data and subsets with name: ``Original Name[X]``, where ``X`` is the number of times the viewer has been cloned.

.. _viewers-scatter-toolbar-detach:

Detach Viewer 
-------------
Under the Focus mode button, there is a |icon-detach| button to detach the viewer from the app. Clicking this button 
opens a new window which displays the viewer of choice.  Use your computer's native exit button to delete the viewer.
Note: anything you do in this viewer is replicated in the main application, and deleting this viewer does **not** delete the viewer in the main application.

If nothing appears, check that popups are allowed on your browser. 


UI Access
=========

.. guidestar-demo:: _static/jdaviz-wireframe.html
   :repeat: false
   :init-steps-json: [{"action":"disable-toolbar-except","value":"loaders"}]
   :steps-json: [{"action": "show-sidebar", "value": "loaders", "delay": 1500, "caption": "Open the data loader"}, {"action": "select-tab", "value": "Viewer", "delay": 1500, "caption": "Select the Viewer tab"}, {"action": "select-dropdown", "value": "Viewer Type:Scatter", "delay": 1500, "caption": "Set viewer type to Scatter"}]