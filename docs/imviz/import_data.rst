.. _imviz-import-data:

*************************
Importing Data into Imviz
*************************

Imviz can load data in the form of a filename (FITS, JPEG, or PNG),
an `~astropy.nddata.NDData` object, or a NumPy array if the data is 2D.
See :meth:`jdaviz.configs.imviz.helper.Imviz.load_data` for more information.

.. note::

    Loading too many datasets will cause performance problem due to
    the number of links necessary; see :ref:`glue:linking-framework`
    for more information.

.. _imviz-import-commandline:

Importing data through the Command Line
---------------------------------------

You can load your data into the Imviz application through the command line::

    jdaviz /my/image/data.fits --layout imviz

.. _imviz-import-gui:

Importing data through the GUI
------------------------------

You can load your data into the Imviz application is
by clicking the :guilabel:`Import Data` button at the top left of the application's
user interface. This opens a dialogue where the user can select a file
that can be parsed as a :class:`~astropy.nddata.NDData`, :class:`~astropy.io.fits.HDUList`,
or :class:`~astropy.io.fits.ImageHDU` in the text field.

After clicking :guilabel:`Import`, the data file will be parsed and loaded into the
application. A notification will appear to let users know if the data import
was successful. Afterward, the new data set can be found in the :guilabel:`Data`
tab of each viewer's options menu as described in :ref:`cubeviz-selecting-data`.

.. _imviz-import-api:

Importing FITS via the API
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
    imviz.load_data("/path/to/data/image.fits")
    imviz.app

Creating Your Own Array
^^^^^^^^^^^^^^^^^^^^^^^

You can create your own array to load into Imviz::

    from astropy.nddata import NDData
    from jdaviz import Imviz

    ndd = NDData(array)
    imviz.load_data(ndd)
    imviz.app

JWST datamodels
^^^^^^^^^^^^^^^

If you have a `jwst.datamodels <https://jwst-pipeline.readthedocs.io/en/latest/jwst/datamodels/index.html>`_
object, you can load it into Imviz as follows::

    import numpy as np
    from astropy.nddata import NDData
    from jdaviz import Imviz

    # mydatamodel is a jwst.datamodels object
    ndd = NDData(np.array(mydatamodel.data), wcs=mydatamodel.get_fits_wcs())
    imviz = Imviz()
    imviz.load_data(ndd)
    imviz.app

There is no plan to natively load such objects until ``datamodels``
is separated out of the ``jwst`` pipeline package.

.. _imviz-import-catalogs-api:

Importing catalogs via the API
------------------------------

If you have a catalog file supported by `astropy.table.Table`, you
can load the catalog into Imviz. Markers are different than Imviz
:ref:`spatial regions <spatial-regions>` as they are only meant to mark catalog positions.
Loading markers can be done with the following commands::

    viewer.marker = {'color': 'green', 'alpha': 0.8, 'markersize': 10, 'fill': False}
    my_markers = Table.read('my_catalog.ecsv')
    coord_i2d = Table({'coord': [SkyCoord(ra=my_catalog['sky_centroid'].ra.degree,
                                          dec=my_catalog['sky_centroid'].dec.degree,
                                          unit="deg")]})
    viewer.add_markers(coord_i2d, use_skycoord=True, marker_name='my_markers')

And to remove those markers::

    viewer.remove_markers(marker_name='my_markers')

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
