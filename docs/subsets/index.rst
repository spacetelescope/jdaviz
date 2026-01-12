.. _subsets:

*******************
Subsets & Regions
*******************

Create and manage spatial and spectral subsets of your data.

.. toctree::
   :maxdepth: 1

   circular
   rectangular
   elliptical
   polygonal
   annulus
   range
   composite

Overview
========

Subsets allow you to select regions of interest in your data for focused analysis:

**Spatial Subsets (2D)**
  - **Circular**: Define circular regions
  - **Rectangular**: Define rectangular regions
  - **Elliptical**: Define elliptical regions
  - **Polygonal**: Define arbitrary polygons
  - **Annulus**: Define annular regions

**Spectral Subsets (1D)**
  - **Range**: Define wavelength/frequency ranges

**Advanced**
  - **Composite**: Combine multiple subsets with boolean operations

Creating Subsets
================

Subsets can be created interactively using the subset tools in the viewer toolbar:

.. code-block:: python

    import jdaviz
    from jdaviz import Imviz

    imviz = Imviz()
    imviz.show()
    imviz.load('image.fits', format='Image')

    # Use the subset tools in the toolbar to create regions

Or programmatically via the API:

.. code-block:: python

    # Create a circular subset
    region = CirclePixelRegion(center=PixCoord(100, 100), radius=20)
    imviz.load_regions(region)

See Also
========

- :doc:`../specviz/plugins` - For spectral subset creation
- Individual subset type pages for detailed information
