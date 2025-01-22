.. _specviz2d-import-data:

*****************************
Importing Data Into Specviz2D
*****************************

By design, Specviz2D only supports data that can be parsed as :class:`~specutils.Spectrum` objects,
as that allows the Python-level interface and parsing tools to be defined in ``specutils``
instead of being duplicated in Jdaviz.
:class:`~specutils.Spectrum` objects are very flexible in their capabilities, however,
and hence should address most astronomical spectrum use cases.
If you are creating your own data products, please read the page :ref:`create_products`.

.. seealso::

    `Reading from a File <https://specutils.readthedocs.io/en/stable/spectrum1d.html#reading-from-a-file>`_
        Specutils documentation on loading data as :class:`~specutils.Spectrum` objects.

Specviz2D can either take both a 2D and 1D spectrum as input, or can automatically extract a 1D
spectrum if only a 2D spectrum is provided.  To view the extraction parameters and override the
extraction, see the :ref:`spectral extraction plugin <specviz2d-spectral-extraction>`.

.. _specviz2d-import-commandline:

Importing data through the Command Line
=======================================

You can load your data into the Specviz2D application through the command line. Providing a data file
is optional and multiple data files are supported (NOTE: this currently only supports passing a 2D
spectrum object and will automatically extract the 1D spectrum):

.. code-block:: bash

    jdaviz --layout=specviz2d /my/directory/spectrum1.fits /my/directory/spectrum2.fits


.. _specviz2d-import-gui:

Importing data through the GUI
==============================

You can load your data into the Specviz2D application
by clicking the :guilabel:`Import Data` button at the top left of the application's
user interface. This opens a dialogue where the user can select a file
that can be parsed as a :class:`~specutils.Spectrum`.

After clicking :guilabel:`Import`, the data file will be parsed and loaded into the
application.

.. _specviz2d-import-api:

Importing data via the API
==========================

Alternatively, users who work in a coding environment like a Jupyter
notebook can access the Specviz2D helper class API. Using this API, users can
load data into the application through code with the
:meth:`~jdaviz.configs.specviz2d.helper.Specviz2d.load_data`
method, which takes as input a :class:`~specutils.Spectrum` object or filename for the
2D spectrum and (optionally) the 1D spectrum.

.. code-block:: python

    specviz2d = Specviz2d()
    specviz2d.load_data('/my/directory/2dspectrum.fits', '/my/directory/1dspectrum.fits')
    specviz2d.show()

By default, extension 1 of the 2D
file is loaded, but you can specify another extension by providing an integer
to the ``ext`` keyword. In case you want to load an uncalibrated spectrum
that is dispersed vertically, you can also set the ``transpose`` keyword to flip
the spectrum to be horizontal:

.. code-block:: python

    specviz2d.load_data(filename, ext=7, transpose=True)

Loading from a URL or URI
-------------------------

.. seealso::

    :ref:`Load from URL or URI <load-data-uri>`
        Imviz documentation describing load from URI/URL.
