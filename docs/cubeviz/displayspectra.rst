******************
Displaying Spectra
******************

A collapsed spectrum of the cube displayed in the upper-left viewer
automatically appears in the 1D spectrum viewer, using the Maximum
collapse method.  The collapse method can be changed in the Viewer
tab of the :guilabel:`Gear` icon in the spectrum viewer. Additional spectra
can be loaded into the spectrum viewer, as detailed in the linked documentation
below. 

.. seealso::

    `Displaying Spectra (Specviz) <https://jdaviz.readthedocs.io/en/latest/specviz/displaying.html>`_
        Documentation on displaying spectra in a 1D spectrum viewer.

The functionality of the `~jdaviz.configs.specviz.Specviz` API can be accessed in Cubeviz via
the `jdaviz.configs.cubeviz.Cubeviz.specviz` attribute, e.g. ``cubeviz.specviz.get_spectra()``.
