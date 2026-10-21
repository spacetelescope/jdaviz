.. _loaders-format-mos:

:dev-only: true

.. rst-class:: section-icon-mdi-plus-box

**********************
MOS Directory Format
**********************

.. warning::

   The MOS directory importer is under active development and is available only
   when ``app.state.dev_mos_loader = True``.

Overview
========

The **MOS** format imports a directory of multi-object spectroscopy products.
It discovers supported files recursively (up to three directory levels) and
routes each product through the existing single-file importer to a compatible
viewer. The importer is currently supported in the generalized (deconfigged)
Jdaviz application only.

Supported Products
==================

The directory must contain at least one 1D spectrum matching ``*_x1d.fits`` or
``*_c1d.fits``. Other supported products are optional:

+-------------------------+----------------------+------------------------+
| Filename pattern        | Product              | Default viewer         |
+=========================+======================+========================+
| ``*_x1d.fits``          | 1D spectrum          | 1D Spectrum            |
+-------------------------+----------------------+------------------------+
| ``*_c1d.fits``          | 1D spectrum          | 1D Spectrum            |
+-------------------------+----------------------+------------------------+
| ``*_s2d.fits``          | 2D spectrum          | 2D Spectrum            |
+-------------------------+----------------------+------------------------+
| ``*_cal.fits``          | 2D spectrum          | 2D Spectrum            |
+-------------------------+----------------------+------------------------+
| ``*_i2d.fits``          | Image                | Image                  |
+-------------------------+----------------------+------------------------+
| ``*_cat.ecsv``          | Source catalog       | Source Catalog Table   |
+-------------------------+----------------------+------------------------+
| ``*_cat.csv``           | Source catalog       | Source Catalog Table   |
+-------------------------+----------------------+------------------------+
| ``*_cat.fits``          | Source catalog       | Source Catalog Table   |
+-------------------------+----------------------+------------------------+

FITS products are checked for readable image or table data before import.
Hidden files and common ``manifest.html`` / README files are ignored; other
unrecognized files make the directory invalid.

API Access
==========

Enable the development flag, select the directory with the file loader, and
choose the ``MOS`` format:

.. code-block:: python

    import jdaviz as jd

    jd.show()
    jd.app.state.dev_mos_loader = True

    ldr = jd.loaders['file']
    ldr.filepath = '/path/to/mos-products'
    ldr.format = 'MOS'

    importer = ldr.importer
    # Optional: extract a 1D spectrum from each 2D spectrum.
    importer.auto_extract_2d = True

    ldr.load()

Importer Options
================

The importer displays a product count and lets you choose an existing or new
viewer for each product type present in the directory. New viewers default to
1D Spectrum, 2D Spectrum, Image, and Source Catalog Table as appropriate.

Data labels use the directory name as a prefix by default, followed by each
filename stem (for example, ``mosdir_jw00000_x1d``). The prefix can be changed
through ``importer.data_label``.

``auto_extract_2d`` is off by default because MOS directories are expected to
include their own 1D spectra. When enabled, a 1D spectrum is also extracted
from each imported 2D spectrum.
