.. _data_menu:
.. rst-class:: section-icon-mdi-alpha-a-box-outline

*********
Data Menu
*********

Control data and subset layer order and visibility for each viewer.

.. toctree::
   :maxdepth: 1

   data_menu

Overview
========

The Data Menu provides controls for managing layers in your viewers, allowing you to:

* Reorder data and subset layers
* Control layer visibility
* Manage which data appears in each viewer

UI Access
=========

.. wireframe-demo::
   :demo: open-data-menu
   :enable-only: loaders
   :demo-repeat: false

API Access
==========

.. code-block:: python

    viewer = jd.viewers['spectrum-viewer']
    data_menu = viewer.data_menu