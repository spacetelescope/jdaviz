.. _data_menu:
.. rst-class:: section-icon-mdi-alpha-a-box-outline

*********
Data Menu
*********

The Data Menu allows you to control data and subset layer order and visibility for each viewer.

.. toctree::
   :maxdepth: 1
   :hidden:

Features
========

* Toggle visibility of data and subset layers
* Reorder layers by dragging
* Control which layers are displayed in each viewer
* Manage layer properties and styling

.. note::
   The Data Menu is accessible from the viewer area and provides fine-grained control over layer display and ordering.

UI Access
=========

.. wireframe-demo:: _static/jdaviz-wireframe.html
   :js: jdaviz-wireframe-actions.js
   :css: jdaviz-wireframe.css
   :repeat: false
   :steps-json: [{"action":"viewer-add","value":"horiz:Image","delay":0},{"action":"viewer-legend","value":"Image:Layer1|Layer2","delay":0},{"action":"pause","delay":1000},{"action":"open-data-menu","value":"Image","delay":0,"caption":"Open the Image viewer data menu"}]

API Access
==========

.. code-block:: python

    viewer = jd.viewers['spectrum-viewer']
    data_menu = viewer.data_menu