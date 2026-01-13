.. _plugins-orientation:

***********

Orientation

***********

.. plugin-availability::

Control image display orientation and alignment.

Description
===========

The Orientation plugin controls how images are displayed, including rotation,
flipping, and alignment to celestial coordinates.

**Key Features:**

* Rotate images
* Flip horizontally/vertically
* Align North up, East left
* Apply to single or all viewers

**Available in:** Imviz, Cubeviz

UI Access
=========

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
