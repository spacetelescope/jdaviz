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

.. wireframe-demo::
   :demo: open-data-menu
   :enable-only:
   :demo-repeat: false

API Access
==========

.. code-block:: python

    viewer = jd.viewers['spectrum-viewer']
    data_menu = viewer.data_menu