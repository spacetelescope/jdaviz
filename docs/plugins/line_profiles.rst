.. _plugins-line_profiles:
.. _imviz-line-profiles:

*************
Line Profiles
*************

.. plugin-availability::

Extract and analyze spatial line profiles from images.

Description
===========

The Line Profiles (XY) plugin extracts pixel values along a line drawn on an image,
showing how flux varies spatially. This is useful for analyzing extended sources,
edges, or gradients.

**Key Features:**

* Extract profiles along arbitrary lines
* Interactive profile plotting
* Multiple data layers
* Export profile data

**Available in:** Imviz, Cubeviz (on 2D slices)

UI Access
=========

Click the :guilabel:`Line Profiles` icon in the plugin toolbar to:

1. Draw a line on the image
2. View the profile plot
3. Export data

API Access
==========

.. code-block:: python

    plg = imviz.plugins['Line Profiles']
    # Access profile data programmatically

.. plugin-api-refs::
   :module: jdaviz.configs.imviz.plugins.line_profile_xy.line_profile_xy
   :class: LineProfileXY

See Also
========

* :ref:`line-profile-xy` - Imviz-specific line profiles documentation
