******************
Displaying Spectra
******************

.. include:: ../_templates/deprecated_config_banner.rst

A collapsed spectrum of the cube displayed in the upper-left viewer
automatically appears in the 1D spectrum viewer, using the set collapse function.
The collapse function can be changed in the :guilabel:`Line`
tab of the Plot Options plugin, which can be reached by clicking the |icon-settings-sliders|
icon in the spectrum viewer. Additional spectra
can be loaded into the spectrum viewer, as detailed in the linked documentation
below.

.. seealso::

    :ref:`Displaying Spectra (Specviz) <specviz-displaying>`
        Documentation on displaying spectra in a 1D spectrum viewer.

There is one important difference when using the API to access Specviz from within Cubeviz.
The functionality of the :class:`jdaviz.configs.specviz.helper.Specviz` API can be accessed in Cubeviz via
the `~jdaviz.configs.cubeviz.helper.Cubeviz.specviz` attribute, e.g. ``cubeviz.specviz.get_spectra()``.
