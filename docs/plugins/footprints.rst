.. _plugins-footprints:
.. rst-class:: section-icon-mdi-tune-variant

**********
Footprints
**********

.. plugin-availability::

Overlay instrument footprints on sky images.

Description
===========

The Footprints plugin displays instrument field-of-view footprints on images,
showing detector layouts and orientations for planning or analysis.

**Key Features:**

* Display JWST/HST instrument footprints
* Position and rotate footprints
* Multiple footprint overlays
* Export footprint regions

This plugin supports loading and overplotting instrument footprint overlays on the image viewers.
Any number of overlays can be plotted simultaneously from any number of the available
preset instruments (requires ``pysiaf`` to be installed), by loading an Astropy regions object from
a file, or by passing an ``STC-S`` string.

The top dropdown allows renaming, adding, and removing footprint overlays.  To modify the display
and input parameters for a given overlay, select the overlay in the dropdown, and modify the choices
in the plugin to change its color, opacity, visibilities in any image viewer in the app.
You can also select between various preset instruments and change the input options
(position on the sky, position angle, offsets, etc).

To import a file, open the "Import" section at the top of the dropdown and select a valid file (must
be able to be parsed by `regions.Regions.read`) from the applicable source.

UI Access
=========

.. wireframe-demo:: _static/jdaviz-wireframe.html
   :js: jdaviz-wireframe-actions.js
   :css: jdaviz-wireframe.css
   :repeat: false
   :init-steps-json: [{"action":"set-plugin","value":"Footprints"}]
   :steps-json: [{"action":"show-sidebar","value":"plugins","delay":1500,"caption":"Open the plugin toolbar"},{"action":"open-panel","value":"Footprints","delay":1000,"caption":"Open the Footprints plugin"}]

Click the :guilabel:`Footprints` icon in the plugin toolbar to:

1. Select instrument
2. Position footprint on image
3. Adjust orientation
4. Toggle visibility

API Access
==========

.. code-block:: python

    plg = jd.plugins['Footprints']
    plg.open_in_tray()
    plg.add_overlay('my imported overlay')  # or fp.rename_overlay to rename an existing entry
    plg.import_region(region)

.. plugin-api-refs::
   :module: jdaviz.configs.imviz.plugins.footprints.footprints
   :class: Footprints
