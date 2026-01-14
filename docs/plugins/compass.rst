.. _plugins-compass:

*******
Compass
*******

.. plugin-availability::

Display orientation compass on images.

Description
===========

The Compass plugin overlays a compass rose on image viewers showing the orientation
of North and East directions based on WCS information.

**Key Features:**

* Show/hide compass overlay
* Auto-update with WCS changes
* Works with multiple viewers

**Available in:** Imviz, Cubeviz

UI Access
=========

Click the :guilabel:`Compass` icon in the plugin toolbar to toggle compass display.

API Access
==========

.. code-block:: python

    plg = imviz.plugins['Compass']
    plg.show = True  # Display compass
    plg.show = False  # Hide compass

.. plugin-api-refs::
   :module: jdaviz.configs.imviz.plugins.compass.compass
   :class: Compass

See Also
========

* :ref:`imviz-compass` - Imviz compass documentation
