.. _imviz-import-data:

***********
Import Data
***********

Imviz can load data in the form of a filename (FITS, JPEG, or PNG),
an `~astropy.nddata.NDData` object, or a NumPy array if the data is 2D.
See :meth:`jdaviz.configs.imviz.helper.Imviz.load_data` for more information.

.. note::

    Loading too many datasets will cause performance problem due to
    the number of links necessary; see :ref:`glue:linking-framework`
    for more information.

Importing data through the GUI
------------------------------

The first way that you can load your data into the Imviz application is
by clicking the :guilabel:`Import` button at the top left of the application's
user interface. This opens a dialogue where the user can select a file
that can be parsed as a :class:`~astropy.nddata.NDData`, :class:`~astropy.io.fits.HDUList`,
or :class:`~astropy.io.fits.ImageHDU` in the text field.

After clicking :guilabel:`Import`, the data file will be parsed and loaded into the
application. A notification will appear to let users know if the data import
was successful. Afterward, the new data set can be found in the :guilabel:`Data`
tab of each viewer's options menu as described in :ref:`cubeviz-selecting-data`.

Importing data via the API
--------------------------

Alternatively, if you are working in a coding environment like a Jupyter
notebook, you have access to the Imviz helper class API. Using this API,
users can load data into the application through code using the :meth:`~jdaviz.configs.imviz.helper.Imviz.load_data`
method, which takes as input either the name of a local file, an
:class:`~astropy.nddata.NDData`, :class:`~astropy.io.fits.HDUList`,
or :class:`~astropy.io.fits.ImageHDU` object.

The example below loads the first science extension of the given FITS file into Imviz::

    from jdaviz import Imviz
    imviz = Imviz()
    imviz.app
    imviz.load_data("/path/to/data/image.fits")

.. _imviz-import-regions-api:

Importing regions via the API
-----------------------------

If you have a region file supported by :ref:`regions:regions_io`, you
can load the regions into Imviz as follows. Any unsupported region will
be skipped with warning and a dictionary of regions that failed to load
will be returned, if any::

    bad_regions = imviz.load_static_regions_from_file("/path/to/data/myregions.reg")

For more details on the API, please see
:meth:`~jdaviz.configs.imviz.helper.Imviz.load_static_regions_from_file`
and :meth:`~jdaviz.configs.imviz.helper.Imviz.load_static_regions` methods
in Imviz.
