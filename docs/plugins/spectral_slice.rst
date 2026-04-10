.. _plugins-spectral_slice:
.. rst-class:: section-icon-mdi-tune-variant

**************
Spectral Slice
**************

.. plugin-availability::

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

To choose a specific slice, enter an approximate wavelength (in which case the nearest slice will
be selected and the wavelength entry will "span" to the exact value of that slice).  The snapping
behavior can be disabled in the plugin settings to allow for smooth scrubbing, in which case the
closest slice will still be displayed in any relevant cube viewers.

Spectrum viewers also contains a tool to allow clicking and
dragging in the spectrum plot to choose the currently selected slice.
When the slice tool is active, clicking anywhere on the spectrum viewer
will select the nearest slice across all viewers, even if the indicator
is off-screen.

For your convenience, there are also player-style buttons with
the following functionality:

* Jump to first
* Previous slice
* Play/Pause
* Next slice
* Jump to last


UI Access
=========

Click the :guilabel:`Spectral Slice` icon or use the slice controls in the
viewer toolbar to navigate through cube slices.

API Access
==========

.. code-block:: python

    plg = jdaviz.plugins['Spectral Slice']
    plg.slice = 50  # Go to slice 50

.. plugin-api-refs::
   :module: jdaviz.configs.cubeviz.plugins.slice.slice
   :class: SpectralSlice

See Also
========

* :ref:`slice` - Slice navigation documentation
