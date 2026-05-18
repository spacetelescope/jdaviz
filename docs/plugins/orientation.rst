.. _plugins-orientation:
.. rst-class:: section-icon-mdi-tune-variant

***********
Orientation
***********

.. plugin-availability::

Control image display orientation and alignment.

.. note::

    This plugin was previous called "Links Control".

Description
===========

This plugin is used to align image layers by pixels or sky (WCS).
All images are automatically linked by pixels on load but you can use
it to re-link by pixels or WCS as needed.

For WCS linking, the "fast approximation" option uses an affine transform
to represent the offset between images, if possible. This method, although less accurate,
is much more performant and should still be accurate to within a pixel for most cases.
If approximation fails, WCS linking will fall back to the full transformation.

Since Jdaviz v3.9, when linking by WCS, a hidden reference data layer
without distortion (labeled "Default orientation") will be created and all the data would be linked to
it instead of the first loaded data. As a result, working in pixel
space when linked by WCS is not recommended. Additionally, any data
with distorted WCS would show as distorted on the display. Furthermore,
any data without WCS can no longer be shown in WCS linking mode.

For the best experience, it is recommended that you decide what kind of
link you want and set it at the beginning of your Imviz session,
rather than later.

For more details on linking, see :ref:`dev_glue_linking`.

**Key Features:**

* Rotate images
* Flip horizontally/vertically
* Align North up, East left
* Apply to single or all viewers

Image Rotation
==============

When linked by WCS, sky rotation is also possible. You can choose from
presets (N-up, E-left/right) or provide your own sky angle.

.. warning::

    Each rotation request creates a new reference data layer in the background.
    Just as in :ref:`imviz-import-data`, the performance would be impacted by
    the number of active rotation layers you have; only keep the desired rotation layer.
    Note that the "default orientation" layer cannot be removed.

UI Access
=========

.. wireframe-demo::
   :demo: plugins,plugins@1000:open-panel
   :enable-only: plugins
   :plugin-name: Orientation
   :plugin-panel-opened: false
   :demo-repeat: false

Click the :guilabel:`Orientation` icon in the plugin toolbar to:

1. Select rotation angle
2. Toggle flip options
3. Click :guilabel:`Align North Up` for WCS alignment
4. Apply to specific viewers or all

API Access
==========

.. code-block:: python

    plg = imviz.plugins['Orientation']
    plg.rotation_angle = 45  # degrees
    plg.align_by_wcs()  # North up, East left

.. plugin-api-refs::
   :module: jdaviz.configs.imviz.plugins.orientation.orientation
   :class: Orientation

See Also
========

* :ref:`imviz-orientation` - Imviz orientation documentation
