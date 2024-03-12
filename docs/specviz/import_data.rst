.. _specviz-import-data:

***************************
Importing Data Into Specviz
***************************

By design, Specviz only supports data that can be parsed as :class:`~specutils.Spectrum` objects,
as that allows the Python-level interface and parsing tools to be defined in ``specutils``
instead of being duplicated in Jdaviz.
:class:`~specutils.Spectrum` objects are very flexible in their capabilities, however,
and hence should address most astronomical spectrum use cases.
If you are creating your own data products, please read the page :ref:`create_products`.

.. seealso::

    `Reading from a File <https://specutils.readthedocs.io/en/stable/spectrum1d.html#reading-from-a-file>`_
        Specutils documentation on loading data as :class:`~specutils.Spectrum` objects.

.. _specviz-import-commandline:

Importing data through the Command Line
=======================================

You can load your data into the Specviz application through the command line. Specifying
a data file is optional, and multiple data files may be provided:

.. code-block:: bash

    jdaviz --layout=specviz /my/directory/spectrum1.fits /my/directory/spectrum2.fits

.. _specviz-import-gui:

Importing data through the GUI
==============================

You can load your data into the Specviz application
by clicking the :guilabel:`Import Data` button at the top left of the application's
user interface. This opens a dialogue where the user can select a file
that can be parsed as a :class:`~specutils.Spectrum`.

After clicking :guilabel:`Import`, the data file will be parsed and loaded into the
application. A notification will appear to let users know if the data import
was successful. Afterward, the new data set can be found in the :guilabel:`Data`
tab of each viewer's options menu as described in :ref:`cubeviz-selecting-data`.

.. _specviz-import-api:

Importing data via the API
==========================

Alternatively, users who work in a coding environment like a Jupyter
notebook can access the Specviz helper class API. Using this API, users can
load data into the application through code with the
:py:meth:`~jdaviz.configs.specviz.helper.Specviz.load_data`
method, which takes as input a :class:`~specutils.Spectrum` object.

FITS Files
----------

The example below loads a FITS file into Specviz:

.. code-block:: python

    from specutils import Spectrum
    spec1d = Spectrum.read("/path/to/data/file")
    specviz = Specviz()
    specviz.load_data(spec1d, data_label="my_spec")
    specviz.show()

You can also pass the path to a file that `~specutils.Spectrum` understands directly to the
:py:meth:`~jdaviz.configs.specviz.helper.Specviz.load_data` method:

.. code-block:: python

    specviz.load_data("path/to/data/file")

Creating Your Own Array
-----------------------

You can create your own array to load into Specviz:

.. code-block:: python

    import numpy as np
    import astropy.units as u
    from specutils import Spectrum
    from jdaviz import Specviz

    flux = np.random.randn(200) * u.Jy
    wavelength = np.arange(5100, 5300) * u.AA
    spec1d = Spectrum(spectral_axis=wavelength, flux=flux)
    specviz = Specviz()
    specviz.load_data(spec1d, data_label="my_spec")
    specviz.show()

JWST datamodels
---------------

If you have a `stdatamodels.datamodels <https://stdatamodels.readthedocs.io/en/latest/jwst/datamodels/index.html#data-models>`_
object, you can load it into Specviz as follows:

.. code-block:: python

    from specutils import Spectrum
    from jdaviz import Specviz

    # mydatamodel is a jwst.datamodels.MultiSpecModel object
    a = mydatamodel.spec[0]
    flux = a.spec_table['FLUX']
    wave = a.spec_table['WAVELENGTH']

    spec1d = Spectrum(flux=flux, spectral_axis=wave)
    specviz = Specviz()
    specviz.load_data(spec1d, data_label="MultiSpecModel")
    specviz.show()

There is no plan to natively load such objects until ``datamodels``
is separated from the ``jwst`` pipeline package.

.. _specviz-multiple-spectra:

Importing a SpectrumList
------------------------

The :py:meth:`~jdaviz.configs.specviz.helper.Specviz.load_data` also accepts
a `~specutils.SpectrumList` object, in which case it will both load the
individual `~specutils.Spectrum` objects in the list and additionally attempt
to stitch together the spectra into a single data object so that
they can be manipulated and analyzed in the application as a single entity:

.. code-block:: python

    from specutils import SpectrumList
    spec_list = SpectrumList([spec1d_1, spec1d_2])
    specviz.load_data(spec_list)
    specviz.show()

In the screenshot below, the combined spectrum is plotted in gray, and one of
the single component spectra are also selected and plotted in red. Note that the
"stitching" algorithm to combine the spectra is a simple concatenation of data,
so in areas where the wavelength ranges of component spectra overlap you may see
the line plot jumping between points of the two spectra, as at the beginning and
end of the red region in the screenshot below:

.. image:: img/spectrumlist_combined.png

This functionality is also available in limited instances by providing a directory path
to the :py:meth:`~jdaviz.configs.specviz.helper.Specviz.load_data` method. Note
that the ``read`` method of :class:`~specutils.SpectrumList` is only set up to handle
directory input in limited cases, for example JWST MIRI MRS data, and will throw an error
in other cases. In cases that it does work, only files in the directory level specified
will be read, with no recursion into deeper folders.

The :py:meth:`~jdaviz.configs.specviz.helper.Specviz.load_data` method also takes
an optional keyword argument ``concat_by_file``. When set to ``True``, the spectra
loaded in the :class:`~specutils.SpectrumList` will be concatenated together into one
combined spectrum per loaded file, which may be useful for MIRI observations, for example.

Loading from a URL or URI
-------------------------

.. seealso::

    :ref:`Load from URL or URI <load-data-uri>`
        Imviz documentation describing load from URI/URL.
