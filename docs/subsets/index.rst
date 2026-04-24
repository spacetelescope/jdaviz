.. _subsets:
.. rst-class:: section-icon-mdi-selection

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
   extensions

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

UI Access
=========

.. wireframe-demo:: _static/jdaviz-wireframe.html
   :repeat: false
   :init-steps-json: [{"action":"disable-toolbar-except","value":"subsets"}]
   :steps-json: [{"action": "show-sidebar", "value": "subsets", "delay": 1500, "caption": "Open the subset tools"}]

Creating Subsets
================

Subsets can be created interactively using the subset tools in the viewer toolbar:

.. code-block:: python

    import jdaviz as jd

    jd.show()
    jd.load('image.fits', format='Image')

    # Use the subset tools in the toolbar to create regions

Or programmatically via the API:

.. code-block:: python

    # Create a circular subset
    from regions import CirclePixelRegion, PixCoord
    region = CirclePixelRegion(center=PixCoord(100, 100), radius=20)
    st = jd.plugins['Subset Tools']
    st.import_region(region)

You can also choose the operation that will be applied by the selector tool
(``replace``, ``add``, ``and``, ``xor``, or ``remove``).

Editing Subsets
===============

If an existing subset is selected, the parameters of the subset will be shown. Note that in addition to parameters for compound
regions (e.g., a subset with multiple disjoint regions) being displayed, the logical operations joining them (``OR``, ``AND``, etc.) are
shown as well for each region. This shows how all regions are added together to create the subset shown in the viewer.

For a simple subset, you can edit its parameters by changing the values
in the corresponding editable text fields. Once you have entered the new
value(s), click :guilabel:`Update` to apply. You should see the subset
parameters, shape, and orientation (if applicable) all update concurrently.

For spatial subsets only, you can choose to recenter the viewer on a single subset or group of subsets. To switch to multiselect mode,
click the icon in the top right of the tool and select multiple subsets from the drop-down menu. The centroid is calculated by
photutils.aperture.ApertureStats.centroid, which is the center-of-mass of the data within the aperture. No background subtraction is
performed. Click Recenter to change its parameters and move it to the calculated centroid. This may take multiple iterations to converge.

.. note::

    If you want accurate centroid calculations, it is recommended that you
    use a background-subtracted image. Alternately, you could calculate
    the centroid outside of Jdaviz (e.g., using ``photutils``) and then
    manually edit the subset (see below) or load your own aperture object
    (:ref:`imviz-import-regions-api`).

Note that angle is reported in degrees as a counter-clockwise rotation about the center. Recentering and rotating subsets
are only applicable to spatial subsets and are unavailable for spectral subsets.

From the API
------------

You can update the attributes of an existing subset via the Subset Tools API. To
see what attributes are available for a given subset, call the ``update_subset`` method
with only the subset specified:

.. code-block:: python

  st = jd.plugins['Subset Tools']
  st.update_subset(subset_label='Subset 1')

This will return a dictionary with the name (as displayed in the UI), attribute, and
value for each editable attribute of each subregion of the specified subset. Note that
passing ``subset_label`` in the ``update_subset`` call will also set the selected subset
in the plugin UI to the specified subset. If ``subset_label`` is not specified,
``update_subset`` will operate on the currently selected subset in the plugin.
The attributes returned by the call above can be updated by passing their new
values as keyword arguments, for example:

.. code-block:: python

  st.update_subset(subset_label='Subset 1', xmin=10, xmax = 20)

In the case of a compound subset, the subregion to update must be specified as well:

.. code-block:: python

  st.update_subset(subset_label='Subset 1', subregion=0, xmin=10, xmax = 20)

You can also create a new subset using the ``import_region`` method. This method takes a
region and either creates a new subset with that region or appends it to another subset
using the ``edit_subset`` and ``combination_mode`` arguments. for example:

.. code-block:: python

  st.import_region(CirclePixelRegion(center=PixCoord(x=4.5, y=4.5), radius=4.5))

will create a new subset but

.. code-block:: python

  st.import_region(CirclePixelRegion(center=PixCoord(x=4.5, y=4.5), radius=4.5), edit_subset='Subset 1',
   combination_mode='or')

will append the region to the existing Subset 1 using the 'or' ``combination_mode``.
Other options for ``combination_mode`` include "and", "andnot", "new", "replace", and "xor".
If you set a value for ``edit_subset`` but not ``combination_mode``, the assumption will be
that the new region is replacing the existing subset named in ``edit_subset``.
This API method acts independently of the UI so all settings from before ``import_region``
was called will be restored afterward.
