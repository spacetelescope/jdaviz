.. _viewers-table:
.. rst-class:: section-icon-mdi-plus-box

*********************************
Source Catalog and Generic Tables
*********************************

Most of the functionality between Source Catalogs and Generic Catalogs viewers 
are identical. The difference between the two are related to how the data is stored in the tables.
 
.. _viewers-table-sourcecatalog:

Source Catalog Table
====================
Source Catalog Table viewers show data loaded with ``format = Source Catalog``. 
In this table, the ``ID``, ``RA``/``X``, ``Dec``/``Y``` columns are the index columns, and the values are not changeable.  

.. _viewers-table-generic:

Generic Table
=============
Generic Table viewers show data loaded with ``format = Generic Catalog``. 
In this table, the ``ID`` column is the index column, and the values are not changeable.  

.. _viewers-table-tablefeatures:

Table viewer features
=====================

- Clicking on a cell shows the cell value in the top gray bar below the toolbar.  On the far left, the column name and
   column number will show in the white box.  On the right, the cell value will be shown in the gray box.
   For non-index cells, to the right of the gray box, a green check and a red x will be shown, indicating the cell
   value can be changed.  Click in the gray box, update the value, and select the green check to apply the value, or
   the red x to disregard the change.  The value in the cell of the table will then be updated. 

- When hovering over or clicking on the column name cell, a small black pencil appears to the right of the column name.
   Selecting the pencil allows you to change the column name.  Select the black check to apply the value, or
   the black x to disregard the change.  The column name will then be updated. 

- The bottom of the viewer shows the number of rows in the page, and allows you to 
   select how many rows to show in the viewer per page.  Select the dropdown to change the row counts.
   To the right is the row and page counter, which tells you which rows you are viewing and how many rows are 
   in the table.  Finally, there are four arrows, which allow you to go to the previous/next or first/final page.

.. _viewers-table-toolbar:

Toolbar
=======

Table Highlight Selection
-------------------------
This |icon-home| icon is only available if at least one Image is displayed in an Image Viewer. 
Clicking on the table highlight selection icon opens up the toolbar. Once open, 
selecting a row in the table will highlight the location of the row (using either Ra/Dec or X/Y pixels)
in the Image Viewer.  Press the ``X`` next to ``TABLE HIGHLIGHT SELECTION`` to exit.  

In the Image Viewer, a ``TABLE HIGHLIGHT SELECTION`` toolbar also appears with four tools.
These include Home, zoom, pan/zoom/center, row selection.  Row Selection is selected by default, 
and allows you to select/de-select rows in the table by clicking on the marker in the image.
Press the ``X`` next to ``TABLE HIGHLIGHT SELECTION`` in the Image Viewer to exit.  


Table Zoom Selection
--------------------
This icon is only available if at least one Image is displayed in an Image Viewer. 
Clicking on the table zoom selection |icon-table-zoom| icon opens up the toolbar. Once open select a row in the table by clicking
the box in each row. 
Then, you can change which viewer to zoom to to the right of the ``TABLE HIGHLIGHT SELECTION`` text. 
Finally, click the orange check mark in the ``TABLE ZOOM SELECTION`` tool to zoom to its location for the 
selected viewer. Press the ``X`` next to ``TABLE HIGHLIGHT SELECTION`` to exit.  

In the Image Viewer, a ``TABLE ZOOM SELECTION`` toolbar also appears with four tools.
These include Home, zoom, pan/zoom/center, row selection.  Row Selection is selected by default, 
and allows you to select/de-select rows in the table by clicking on the marker in the image.
Press the ``X`` next to ``TABLE HIGHLIGHT SELECTION`` to exit.  

Table Subset Selection
----------------------
Clicking on the table subset selection |icon-table-subset| icon icon opens up the toolbar.  Once open, select 
a row(s) in the table by clicking the bor in each row. Then, click the check mark 
in the ``TABLE SUBSET SELECTION`` tool to create a subset. Press the ``X`` next to ``TABLE SUBSET SELECTION`` to exit.  

In the Image Viewer, a ``TABLE SUBSET SELECTION`` toolbar also appears with four tools.
These include Home, zoom, pan/zoom/center, row selection.  Row Selection is selected by default, 
and allows you to select/de-select rows in the table by clicking on the marker in the image.
Press the ``X`` next to ``TABLE SUBSET SELECTION`` to exit.  

Add Column 
----------
Clicking on the add column |icon-column-add| icon opens up the toolbar.  Once open, you can type in a 
column name and a fill value for the column.  Click the check mark next to the fill value to 
create the column. 

Press the ``X`` next to ``ADD COLUMN`` to exit.  

Visible Columns
---------------
Clicking on the visible columns |icon-column-visible| icon opens up the toolbar.  Once open, you can 
select from the dropdown in the toolbar which columns to show in the table viewer.  Selecting/unselecting
the column names.  As you select/deselect columns, the table will automatically update. 
These columns are not deleted from jdaviz, they are just hidden from view in the viewer.   
Press the ``X`` next to ``VISIBLE COLUMNS`` to exit.  

Focus mode 
----------
Clicking on the |icon-focus| focus mode button expands the viewer to fill the application.  
The right hand plugin feature is not accessible in the UI. Hovering over a pixel show the cursor information. 
Click on the |icon-focus-exit| focus mode exit button to exit. 

Clone Viewer
------------
Under the Focus mode button, there is a |icon-clone| button to clone the viewer. Clicking this button duplicates the viewer with the same
data and subsets with name: ``Original Name[X]``, where ``X`` is the number of times the viewer has been cloned.

Detach Viewer 
-------------
Under the Focus mode button, there is a |icon-detach| button to detach the viewer from the app. Clicking this button 
opens a new window which displays the viewer of choice.  Use your computer's native exit button to delete the viewer.
Note: anything you do in this viewer is replicated in the main application, and deleting this viewer does **not** delete the viewer in the main application.

If nothing appears, check that popups are allowed on your browser. 

.. _viewers-table-ui:

UI Access
=========

.. guidestar-demo:: _static/jdaviz-wireframe.html
   :repeat: false
   :init-steps-json: [{"action":"disable-toolbar-except","value":"loaders"}]
   :steps-json: [{"action": "show-sidebar", "value": "loaders", "delay": 1500, "caption": "Open the data loader"}, {"action": "select-tab", "value": "Viewer", "delay": 1500, "caption": "Select the Viewer tab"}, {"action": "select-dropdown", "value": "Viewer Type:Table", "delay": 1500, "caption": "Set viewer type to Table"}]