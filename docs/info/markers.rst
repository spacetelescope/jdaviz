.. _deconfigged-info-markers:
.. rst-class:: section-icon-mdi-information-outline

*******
Markers
*******

Overview
========

This tool allows for interactively creating markers in any viewer and logging information about
the location of that marker along with the applicable data and viewer labels into a table. It also
allows the user to measure distances between points in a viewer.

UI Access
=========

.. wireframe-demo::
   :demo: info,info:select-tab=Markers
   :enable-only: info
   :demo-repeat: false

Details
=======

With the Markers tool open in the Information tab , mouse over any viewer and press the "m" key to log the information
displayed in the app toolbar into the table.  The markers remain at that fixed pixel-position in
the viewer they were created (regardless of changes to the underlying data or linking,
see :ref:`dev_glue_linking`) and are only visible when the plugin is opened.

When images are WCS linked, the table also exposes columns labeled "pixel:unreliable", "world:unreliable",
and "value:unreliable".  These will be logged as ``True`` in cases where the information is outside
the bounds of the reference image's WCS (noted in the mouseover display by the information showing
as grayed).

.. _distance-tool:

Distance Tool
-------------

The Markers plugin also includes a tool for measuring the distance and position angle between
two points in a viewer. This functionality is available whenever the Markers plugin is open.


1. Mouse over the desired start point in a viewer and press the ``d`` key. A ``...`` indicator
   will appear in the :guilabel:`Last Measured Distance` field at the bottom of the plugin,
   showing that the first point is set.
2. Mouse over the desired end point and press the ``d`` key again.

This will draw a line between the two points. A label showing the distance will appear,
rotated to be parallel with the line, and offset to prevent intersecting the line.

A new table, :guilabel:`Measurements`, will also appear below the main markers table. This
table logs the start and end coordinates (both pixel and world, if available), the on-sky
separation, the pixel distance, and the position angle for each measurement.

**Additional Features:**

* **Snapping**: To measure the distance from or to an existing marker, hold down the ``Alt`` key
  (or ``Option`` on Mac) when you press ``d``. The tool will "snap" to the nearest marker
  already in the main table.
* **Clearing**: Pressing the ``r`` key will clear all markers from the main table *and* all
  distance lines from the viewers.



API Access
==========

To export the table into the notebook or clear the table via the API:

.. code-block:: python

    markersplugin = jd.plugins['Markers']
    t = markersplugin.export_table()
    markersplugin.clear_table()
