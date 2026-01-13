.. _plugins-spectral_slice:

**************
Spectral Slice
**************

Navigate and visualize spectral slices in cubes.

Description
===========

The Spectral Slice plugin provides controls for navigating through wavelength
slices in spectral cubes and managing slice display.

**Key Features:**

* Slice navigation controls
* Wavelength indicator
* Slice animation
* Synchronize across viewers

**Available in:** Cubeviz

UI Access
=========

Click the :guilabel:`Spectral Slice` icon or use the slice controls in the
viewer toolbar to navigate through cube slices.

API Access
==========

.. code-block:: python

    plg = cubeviz.plugins['Spectral Slice']
    plg.slice = 50  # Go to slice 50

.. plugin-api-refs::
   :module: jdaviz.configs.cubeviz.plugins.slice.slice
   :class: SpectralSlice

See Also
========

* :ref:`slice` - Slice navigation documentation
