.. _plugins-footprints:

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

**Available in:** Imviz

UI Access
=========

Click the :guilabel:`Footprints` icon in the plugin toolbar to:

1. Select instrument
2. Position footprint on image
3. Adjust orientation
4. Toggle visibility

API Access
==========

.. code-block:: python

    plg = imviz.plugins['Footprints']
    # Add and configure footprints programmatically

.. plugin-api-refs::
   :module: jdaviz.configs.imviz.plugins.footprints.footprints
   :class: Footprints

See Also
========

* :ref:`imviz-footprints` - Footprints documentation
