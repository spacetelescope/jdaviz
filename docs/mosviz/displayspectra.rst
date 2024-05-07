******************
Displaying Spectra
******************

The spectra linked to the source selected in the table viewer will be automatically displayed in the viewers,
with 2d spectra populating the top right viewer, and 1d spectra populating the viewer 2nd from top on the right.

.. seealso::

    :ref:`Display Spectra <specviz-displaying>`
        Specviz documentation on displaying spectra.

The functionality of the Specviz API can be accessed in Mosviz via
the `~jdaviz.configs.mosviz.helper.Mosviz.specviz` attribute, e.g.,
``mosviz.specviz.get_spectra()``.

Pan/Zoom
========

For an overview on general pan/zoom functionality, please see :ref:`imviz_pan_zoom`

Synchronous Spectral Pan/Zoom
-----------------------------
Mosviz assumes the 1D and 2D spectra objects share a relationship in spectral space. As a result, the 1D and 2D spectral viewers have their spectral axes (the horizontal x-axis) linked. As you pan and zoom in spectral space (horizontally) in either of the two spectral viewers, the other will follow, simultaneously panning and zooming by the same amounts.

Defining Spectral Regions
=========================

For an overview on spectral regions, please see :ref:`spectral-regions`

Plot Settings
=============

Plot settings for the 1d spectrum viewer can be found in the Specviz section.

.. seealso::

    :ref:`Plot Settings <specviz-plot-settings>`
        Specviz documentation on plot settings for a 1d spectrum viewer.

Display settings for the 2d spectrum viewer can be found in the Cubeviz section.

.. seealso::

    :ref:`Display Settings <imviz-display-settings>`
        Cubeviz documentation on display settings for an image viewer (2d spectrum viewer in this case).
