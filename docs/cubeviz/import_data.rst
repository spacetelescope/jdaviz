.. _cubeviz-import-data:

***********
Import Data
***********

There are two primary ways in which you can load your data into the Cubeviz
application:

* :ref:`gui-import-cubeviz`
* :ref:`api-import-cubeviz`

Cubeviz supports loading the following data formats:

* FITS file, `~astropy.io.fits.HDUList`, `~astropy.io.fits.ImageHDU`, or
  `~astropy.io.fits.PrimaryHDU` that can be parsed as
  `~specutils.Spectrum1D` 3D object, in which case the application
  will attempt to automatically parse the data into the viewers as described
  in :ref:`cubeviz-display-cubes`. This support includes the ASDF-in-FITS
  format for JWST but the ASDF/GWCS extension will be ignored.
* If a `~specutils.Spectrum1D` 3D object is passed in directly, it will
  be loaded into the different viewers based on its ``flux``, ``mask``,
  or ``uncertainty`` attributes.
* If a `~specutils.Spectrum1D` 1D object is passed in directly, it will
  be loaded into the 1D spectrum viewer even though for this use case,
  :ref:`specviz` is better suited instead of Cubeviz.
* If a 3D Numpy array is passed in directly, a dummy WCS will be assigned.
  It will be loaded into the flux viewer unless an extra keyword option,
  ``data_type`` is provided to indicate ``'mask'`` or ``'uncert'``.

.. _gui-import-cubeviz:

Importing data through the GUI
------------------------------

The first way you can load your data into the Cubeviz application is
by clicking the :guilabel:`Import` button at the top left of the application's 
user interface. This opens a dialogue where you can navigate your local
file system (single click to enter a folder) and select the path of a file 
that can be parsed as a :class:`~specutils.Spectrum1D`:

.. image:: img/cubeviz_import_data.png

After clicking :guilabel:`Import`, the data file will be parsed and loaded into the 
application. A green success message will appear if the data import 
was successful. Afterward, the new data set can be found in the :guilabel:`Data` 
tab of each viewer's options menu as described in :ref:`cubeviz-selecting-data`.

Due to the limitations of GUI interactions, only filenames are accepted as inputs.
If you wish to load native Python objects, see :ref:`api-import-cubeviz`.

.. _api-import-cubeviz:

Importing data via the API
--------------------------

Alternatively, if you are working in a coding environment like a Jupyter
notebook, you have access to the Cubeviz helper class API. Using this API,
you can load data into the application through code using the
:meth:`~jdaviz.core.helpers.ConfigHelper.load_data`
method, which takes as input either the name of a local file or a 
:class:`~specutils.Spectrum1D` object.

    >>> from jdaviz import Cubeviz
    >>> cubeviz = Cubeviz()
    >>> cubeviz.load_data("/Users/demouser/data/cube_file.fits")  # doctest: +SKIP

Theoretically, mix-and-match loading might be possible. For instance,
you may choose to load `~specutils.Spectrum1D` into one viewer, `~astropy.io.fits.ImageHDU`
into another, and Numpy array into the third one. However, user must ensure their
data units and WCS's are compatible. Therefore, while possible, it is not recommended unless
you know what you are doing.

For more examples on loading different formats, see
``notebooks/concepts/cubeviz_parser_showcase.ipynb``.
