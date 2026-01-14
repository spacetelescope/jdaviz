.. _plugins-slit_overlay:
.. _specviz2d-slit-overlay:

************
Slit Overlay
************

.. plugin-availability::

Overlay spectrograph slit positions on images.

Description
===========

The Slit Overlay plugin displays the slit position and orientation from 2D
spectroscopic observations overlaid on associated images or spatial maps.

**Key Features:**

* Display slit positions from WCS
* Overlay on images
* Multiple slit support
* Adjust visibility

**Available in:** Specviz2d

UI Access
=========

Click the :guilabel:`Slit Overlay` icon in the plugin toolbar to configure
slit overlay display options.

API Access
==========

.. code-block:: python

    plg = specviz2d.plugins['Slit Overlay']
    plg.show = True

.. plugin-api-refs::
   :module: jdaviz.configs.mosviz.plugins.slit_overlay.slit_overlay
   :class: SlitOverlay
