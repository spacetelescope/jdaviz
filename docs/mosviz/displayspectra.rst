******************
Displaying Spectra
******************

The spectra linked to the source selected in the table viewer will be automatically displayed in the viewers,
with 2d spectra populating the top right viewer, and 1d spectra populating the viewer 2nd from top on the right.

.. seealso::

    `Display Spectra <https://jdaviz.readthedocs.io/en/latest/specviz/displaying.html#>`_
        Specviz documentation on displaying spectra.

Pan/Zoom
========

For an overview on general pan/zoom functionality, please see :ref:`pan-zoom`

Synchronous Spectral Pan/Zoom
-----------------------------
Mosviz assumes the 1D and 2D spectra objects share a relationship in spectral space. As a result, the 1D and 2D spectral viewers have their spectral axes (the horizontal x-axis) linked. As you pan and zoom in spectral space (horizontally) in either of the two spectral viewers, the other will follow, simultaneously panning and zooming by the same amounts.

.. warning::
    If you pan too far away from the bounds of the dataset provided in the 1D or 2D spectral viewers, a warning will be displayed to notify the user. If you go too far, there is a risk of desynchronizing the two viewers.

Defining Spectral Regions
=========================

For an overview on spectral regions, please see :ref:`spectral-regions`

Plot Settings
=============

Plot settings for the 1d spectrum viewer can be found in the Specviz section.

.. seealso::

    `Plot Settings <https://jdaviz.readthedocs.io/en/latest/specviz/displaying.html#plot-settings>`_
        Specviz documentation on plot settings for a 1d spectrum viewer.

Display settings for the 2d spectrum viewer can be found in the Cubeviz section.

.. seealso::

    `Display Settings <https://jdaviz.readthedocs.io/en/latest/cubeviz/displaycubes.html#display-settings>`_
        Cubeviz documentation on display settings for an image viewer (2d spectrum viewer in this case).
