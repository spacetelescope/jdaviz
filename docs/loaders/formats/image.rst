.. _loaders-format-image:
.. rst-class:: section-icon-mdi-plus-box

:data-types: image

*********************
Image Format
*********************

Load two-dimensional astronomical images.

Overview
========

The Image format is used for loading 2D astronomical imaging data, such as direct
images from cameras and imagers.

Usage
=====

.. code-block:: python

    import jdaviz
    jdaviz.show()

    # Load an image
    jdaviz.load('image.fits', format='Image')

Data Requirements
=================

The data should be a 2D array where:

- Each pixel represents a spatial position on the sky
- Pixel values represent flux/intensity measurements

Images can be in various coordinate systems and may include WCS (World Coordinate System)
information for relating pixel positions to sky coordinates.

Supported File Formats
======================

- FITS files with 2D image data
- ASDF files with image data
- JWST imaging data (i2d files)
- HST imaging data

UI Access
=========

.. guidestar-demo:: _static/jdaviz-wireframe.html
   :repeat: false
   :init-steps-json: [{"action":"disable-toolbar-except","value":"loaders"}]
   :steps-json: [{"action": "show-sidebar", "value": "loaders", "delay": 1500, "caption": "Open the data loader"}, {"action": "select-dropdown", "value": "Format:Image", "delay": 1000, "caption": "Set format to Image"}, {"action": "highlight", "target": "#format-select", "delay": 1500}]

Data Association (Parent Dataset)
=================================

When loading a file with multiple extensions (e.g. a FITS file with ``SCI``, ``ERR``,
and ``DQ`` extensions), the importer can *associate* extensions with one another by
setting up a parent-child relationship. An associated (child) data entry is nested
under its parent in the data menu and is treated as a layer of the parent rather than
as an independent image, e.g., child layers are **not** cycled through when
:ref:`blinking <imviz-blinking>`; only top-level (parent) data are blinked.

The ``Parent Dataset`` dropdown controls this behavior:

- **Auto** (default): non-science extensions (e.g. ``ERR``, ``DQ``) are automatically
  associated with the matching science extension (``SCI``/``DATA`` of the same version).
  The science parent may either be loaded in the same import or already present in the
  data collection from an earlier load (matched by an internal labeling mechanism), so
  loading an ``ERR`` extension later still associates it with a previously-loaded ``SCI``
  extension.
- **None**: no association is created, even when multiple extensions are imported. Each
  extension is loaded as an independent, top-level data entry.
- **A specific dataset**: associate the new data as a child of the selected dataset.

.. code-block:: python

    ldr = jdaviz.loaders['file']
    ldr.filename = 'image.fits'
    ldr.format = 'Image'

    # default 'Auto' associates ERR/DQ with their SCI extension
    ldr.importer.parent = 'Auto'

    # disable association entirely
    ldr.importer.parent = 'None'

See Also
========

- :doc:`../../imviz/displayimages` - For information on displaying images
- :doc:`../../imviz/plugins` - For photometric analysis
