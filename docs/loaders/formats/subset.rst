.. _loaders-format-subset:
.. rst-class:: section-icon-mdi-plus-box

:data-types: subset

*************
Subset Format
*************

Load spatial or spectral regions as subsets for analysis.

Overview
========

The Subset format is used for importing region definitions that define spatial or
spectral selections within your data. Subsets can be used to analyze specific areas
of interest, extract statistics, or filter data.

Usage
=====

.. code-block:: python

    import jdaviz
    from regions import Regions

    jd = jdaviz.show()

    # Load a subset from a region file
    jd.load('my_region.reg', format='Subset')

    # Or load a regions object directly
    regions = Regions.read('my_region.reg')
    jd.load(regions, format='Subset', subset_label='My Region')

Data Requirements
=================

The data should be either:

- **Spatial regions**: For 2D image data (Imviz, Cubeviz), using the
  `~regions.Regions` format with sky coordinates
- **Spectral regions**: For 1D or 2D spectral data (Specviz, Specviz2D),
  using `~specutils.SpectralRegion` format

For spatial regions, the regions must have sky coordinates (not pixel coordinates)
that can be converted to pixel coordinates in the target viewer.

Supported File Formats
======================

- DS9 region files (.reg)
- FITS region files (.fits)
- ECSV files for spectral regions (.ecsv)
- STCS string format
- Python objects: `~regions.Regions` or `~specutils.SpectralRegion`

The parser automatically detects the format based on file extension and content.

Subset Label
============

When importing a subset, you can specify a custom label:

.. code-block:: python

    jd.load('my_region.reg', format='Subset', subset_label='Custom Name')

If no label is provided, the subset will be automatically named "Subset N" where
N is the next available number in the subset sequence.

UI Access
=========

.. wireframe-demo::
   :demo: loaders,loaders@1000:select-dropdown=Format:Subset,loaders:highlight=#format-select
   :enable-only: loaders
   :demo-repeat: false

See Also
========

- :ref:`export-subsets` - Exporting subsets for reuse
