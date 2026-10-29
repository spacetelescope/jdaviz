.. _data_menu:
.. rst-class:: section-icon-mdi-alpha-a-box-outline

*********
Data Menu
*********

The Data Menu allows you to control data and subset layer order and visibility for each viewer.
Click on the gray viewer number in the top right corner of the viewer to access in the UI.  

.. toctree::
   :maxdepth: 1
   :hidden:

Features
========

* Toggle visibility of data and subset layers
* Reorder layers by dragging:  Click and drag a data or subset layer up or down to change the order of the layers
* Control which layers are displayed in each viewer
* Manage layer properties and styling

.. note::
   The Data Menu is accessible from the viewer area and provides fine-grained control over layer display and ordering.

Renaming
--------
When hovering over a data or subset layer, a pencil icon appears.  Clicking this icons allows you to rename the data layer. 

Copy
----

Clicking the clickboard icon next to the data or subset layer name copies the layer name to your clipboard.  

Visibility 
----------
Clicking the |icon-eye| eyeball icon next to the data or subset layer name toggles the visibility of the layer. 

Adding data
-----------

Clicking on the ``+`` in the top right corner of the data menu allows you to add data already loaded 
into ``jdaviz`` or create subsets. 

Orientation
-----------
For ``Image`` Viewers, the top left of the data menu shows the alignment of the image. 
Clicking on the compass icon opens the ``Orientation`` plugin allowing you to change the orientation.

Trash can
---------
After clicking on data or subset layer(s), clicking the trashcan icon allows you to either:

- Remove from viewer: removes the layer from the viewer, but the dataset is still loaded in the app
- Delete from app: deletes the dataset from ``jdaviz``.  You must use the ``Loader`` plugin to reload the data.

Tag 
---

After clicking on data or subset layer(s), clicking the tag icon opens up the ``Metadata`` 
plugin for the selected data.  

.. _data_menu-edit_subsets:

Edit subset
-----------

If a subset layer is in the data menu, when you select it, an ``EDIT SUBSET`` icon appears 
on the bottom right of the data menu.  
After clicking ``EDIT SUBSET`` another menu opens with the following items: 

* ``Resize in Viewer`` allows you to resize the subset directly in the viewer by dragging the white boxes on the corners.
* ``Edit in plugin`` opens up the Subset tools plugin. 

Below are several options: 

* ``replace``: will remove the previously created selection and place the newly created subset.
* ``or``: allows you to create another subset that extends the existing subset.
* ``and``: only leaves behind the overlapping region between the existing subset and any additional subsets.
* ``xor``: only leaves behind the non-overlapping region between the existing subset and any additional subsets.
* ``andnot``: will de-select any parts of the existing subset that overlaps with any additional subsets.

You can use these options to further adjust the region of interest and adapt it to your use case.


UI Access
=========

.. guidestar-demo:: _static/jdaviz-wireframe.html
   :js: jdaviz-wireframe-actions.js
   :css: jdaviz-wireframe.css
   :repeat: false
   :steps-json: [{"action":"viewer-add","value":"horiz:Image","delay":0},{"action":"viewer-legend","value":"Image:Layer1|Layer2","delay":0},{"action":"pause","delay":1000},{"target":".jdaviz-viewer[data-viewer-id='Image'] .jdaviz-viewer-legend","action":"highlight","delay":1500,"caption":"Click the viewer legend"},{"action":"open-data-menu","value":"Image","delay":0,"caption":"Open the Image viewer data menu"}]



API Access
==========

.. code-block:: python

    viewer = jd.viewers['spectrum-viewer']
    data_menu = viewer.data_menu