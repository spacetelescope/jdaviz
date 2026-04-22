.. _loaders-format-footprint:
.. rst-class:: section-icon-mdi-plus-box

:data-types: footprint

****************
Footprint Format
****************

Load sky footprints for instrument field-of-view visualization.

Overview
========

The Footprint format is used for importing sky region footprints that represent
instrument fields of view, observing apertures, or other spatial overlays.
Footprints are displayed as overlays on images and can be used to plan observations
or visualize coverage.

Usage
=====

.. code-block:: python

    import jdaviz
    from regions import Regions

    jd = jdaviz.show()

    # Load a footprint from a region file
    jd.load('instrument_fov.reg', format='Footprint')

    # Or load a regions object with a custom label
    regions = Regions.read('aperture.reg')
    jd.load(regions, format='Footprint', footprint_label='JWST NIRCam')

Data Requirements
=================

The data should be spatial regions in sky coordinates:

- **Region types**: Any region supported by the `~regions` package (circles,
  rectangles, polygons, etc.)
- **Coordinate system**: Must have sky coordinates (not pixel coordinates) that
  can be converted to pixel coordinates using the image WCS
- **Format**: Single `~regions.Region` or `~regions.Regions` collection

Supported File Formats
======================

- DS9 region files (.reg)
- FITS region files (.fits)
- Python objects: `~regions.Region` or `~regions.Regions`

Footprint Label
===============

When importing a footprint, you can specify a custom label:
.. code-block:: python

    jd.load('fov.reg', format='Footprint', footprint_label='Instrument FOV')

If no label is provided, the default label 'default' will be used. This label specifies the name of the overlay layer that represents the Footprint region which can be modified in the Footprints plugin. 

UI Access
=========

.. wireframe-demo:: _static/jdaviz-wireframe.html
   :js: jdaviz-wireframe-actions.js
   :css: jdaviz-wireframe.css
   :repeat: false
   :steps-json: [{"action":"show-sidebar","value":"loaders","delay":1500},{"action":"select-dropdown","value":"Format:Footprint","delay":1000},{"action":"highlight","target":"#format-select","delay":1500}]

See Also
========

- :ref:`plugins-footprints` - Footprints plugin for visualizing and managing footprints