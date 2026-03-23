.. _plugins-image-profiles:
.. rst-class:: section-icon-mdi-tune-variant

*************************
Image Profiles (X/Y cuts)
*************************

.. plugin-availability::

Extract and analyze spatial line profiles from images.

Description
===========

This plugin extracts pixel values along a line drawn on an image,
showing how flux varies spatially. This is useful for analyzing extended sources,
edges, or gradients.. The line profiles in X and Y can be extracted by either:
pressing ``l`` at the desired pixel location on the image viewer while the plugin is open,
or by manually specifying the pixel coordinates X and Y, before selecting the :guilabel:`PLOT`
button. The top visible image, the same one displayed under :ref:`imviz-compass`,
will be used for these plots.

This plugin only considers pixel locations, not sky coordinates.

**Key Features:**

* Extract profiles along arbitrary lines
* Interactive profile plotting
* Multiple data layers
* Export profile data

UI Access
=========

Click the :guilabel:`Image Profiles (XY)` icon in the plugin toolbar to:

1. Draw a line on the image
2. View the profile plot
3. Export data

API Access
==========

.. code-block:: python

    plg = jd.plugins['Image Profiles (XY)']
    # Access profile data programmatically

.. plugin-api-refs::
   :module: jdaviz.configs.imviz.plugins.line_profile_xy.line_profile_xy
   :class: LineProfileXY

See Also
========

* :ref:`line-profile-xy` - Imviz-specific line profiles documentation
