*************************
Loading Data into Specviz
*************************

By design, Specviz only supports data that can be parsed as :class:`~specutils.Spectrum1D` objects, as that allows the Python-level interface and parsing tools to be defined in `specutils` instead of being duplicated in `jdaviz`.  :class:`~specutils.Spectrum1D` objects are very flexible in their capabilities, however, and hence should address most astronomical spectrum use cases.

.. seealso::

    `Reading from a File <https://specutils.readthedocs.io/en/stable/spectrum1d.html#reading-from-a-file>`_
        Specutils documentation on loading data as :class:`~specutils.Spectrum1D` objects.

There are two primary ways in which a user can load their data into the Specviz application: through the UI, or via the Python API (for most user cases this means inside a notebook).  These are separately detailed below.

Importing data through the GUI
------------------------------

The first way that users can load their data into the Specviz application is by using the "Import Data" button in the application's user interface.

.. image:: img/specviz_viewer.png

This process is fairly straightforward, users need only click on the "Import Data" button:

.. image:: img/import_data_1.png

and enter the path of file that can be parsed as a :class:`~specutils.Spectrum1D` in the text field:

.. image:: img/import_data_2.png

After clicking "Import", the data file will be parsed and loaded into the application. A notification will appear to let users know if the data import was successful. Afterward, the new data set can be found in the "Data" tab of each viewer's options menu.
To access the data tab, click the "hammer and screwdriver" icon to open the tool menu of a viewer. Then, click the "gear" icon.

.. image:: img/import_data_3.png

Here, users can select the loaded data set to be visualized in the viewer.

.. image:: img/data_selected_1.png

.. _api-import:

Loading data via the API
------------------------
Alternatively, if users are working in a coding environment like a Jupyter notebook, they have access to the :class:`~jdaviz.configs.specviz.helper.Specviz` helper class API. Using this API, users can load data into the application through code.
Below is an example of importing the :class:`~jdaviz.configs.specviz.helper.Specviz` helper class, creating a :class:`~specutils.Spectrum1D` object from a data file via the :func:`~specutils.Spectrum1D.read` method::

    >>> from specutils import Spectrum1D
    >>> spec1d = Spectrum1D.read("/path/to/data/file") #doctest: +SKIP
    >>> specviz = SpecViz() #doctest: +SKIP
    >>> specviz.load_spectrum(spec1d)  #doctest: +SKIP

This method works well for data files that `specutils` understands.  However, if you are using your own data file or in-memory data, you can instead create a :class:`~specutils.Spectrum1D` object directly. In this example that is done using randomly generated data, and then that :class:`~specutils.Spectrum1D` object is loaded into the Specviz application::

    >>> from jdaviz.configs.specviz.helper import SpecViz
    >>> import numpy as np
    >>> import astropy.units as u
    >>> from specutils import Spectrum1D
    >>> flux = np.random.randn(200)*u.Jy
    >>> wavelength = np.arange(5100, 5300)*u.AA
    >>> spec1d = Spectrum1D(spectral_axis=wavelength, flux=flux)
    >>> specviz = SpecViz()
    >>> specviz.load_spectrum(spec1d)

For more information about using the Specutils package, please see the
`Specutils documentation <https://specutils.readthedocs.io>`_.
