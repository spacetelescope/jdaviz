.. _imviz-import-data:

*************************
Importing Data into Imviz
*************************

Imviz can load data in the form of a filename (FITS, JPEG, or PNG),
an `~astropy.nddata.NDData` object, or a NumPy array if the data is 2D.
See :meth:`jdaviz.configs.imviz.helper.Imviz.load_data` for more information.

.. note::

    Loading too many datasets will cause performance problems due to
    the number of links necessary; see :ref:`glue:linking-framework`
    for more information.

.. _imviz-import-commandline:

Importing data through the Command Line
=======================================

When running the Imviz application via the command line, you must provide a path
to a compatible file, which will be loaded into the app on initialization:

.. code-block:: bash

    jdaviz imviz /my/image/data.fits

.. _imviz-import-gui:

Importing data through the GUI
==============================

You can load your data into the Imviz application
by clicking the :guilabel:`Import Data` button at the top left of the application's
user interface. This opens a dialogue where the user can select a file
that can be parsed as a :class:`~astropy.nddata.NDData`, :class:`~astropy.io.fits.HDUList`,
or :class:`~astropy.io.fits.ImageHDU` in the text field.

After clicking :guilabel:`Import`, the data file will be parsed and loaded into the
application. A notification will appear to let users know if the data import
was successful. Afterward, the new data set can be found in the :guilabel:`Data`
tab of each viewer's options menu as described in :ref:`cubeviz-selecting-data`.

.. _imviz-import-api:

Importing data via the API
==========================

Alternatively, users who work in a coding environment like a Jupyter
notebook can access the Imviz helper class API. Using this API, users can
load data into the application through code with the
:meth:`~jdaviz.configs.imviz.helper.Imviz.load_data`
method, which takes as input either the name of a local file or an
:class:`~astropy.nddata.NDData`, :class:`~astropy.io.fits.HDUList`,
or :class:`~astropy.io.fits.ImageHDU` object.

FITS Files
----------

The example below loads the first science extension of the given FITS file into Imviz:

.. code-block:: python

    from jdaviz import Imviz
    imviz = Imviz()
    imviz.load_data("/path/to/data/image.fits")
    imviz.show()

Creating Your Own Array
-----------------------

You can create your own array to load into Imviz:

.. code-block:: python

    import numpy as np
    from jdaviz import Imviz

    arr = np.arange(100).reshape((10, 10))
    imviz = Imviz()
    imviz.load_data(arr, data_label='my_array')
    imviz.show()

JWST datamodels
---------------

If you have a `jwst.datamodels <https://jwst-pipeline.readthedocs.io/en/latest/jwst/datamodels/index.html>`_
object, you can load it into Imviz as follows:

.. code-block:: python

    import numpy as np
    from astropy.nddata import NDData
    from jdaviz import Imviz

    # mydatamodel is a jwst.datamodels object
    ndd = NDData(np.array(mydatamodel.data), wcs=mydatamodel.get_fits_wcs())
    imviz = Imviz()
    imviz.load_data(ndd, data_label='my_data_model')
    imviz.show()

There is no plan to natively load such objects until ``datamodels``
is separated from the ``jwst`` pipeline package.

.. _imviz-import-catalogs-api:

Importing catalogs via the API
==============================

If you have a catalog file supported by `astropy.table.Table`, you
can load the catalog into Imviz and add markers to Imviz viewers to show
positions from the catalog. These markers are different than Imviz
:ref:`spatial regions <imviz_defining_spatial_regions>` as they are only meant to mark catalog positions.
Loading markers can be done with the following commands:

.. code-block:: python

    viewer.marker = {'color': 'green', 'alpha': 0.8, 'markersize': 10, 'fill': False}
    my_markers = Table.read('my_catalog.ecsv')
    coord_i2d = Table({'coord': [SkyCoord(ra=my_catalog['sky_centroid'].ra.degree,
                                          dec=my_catalog['sky_centroid'].dec.degree,
                                          unit="deg")]})
    viewer.add_markers(coord_i2d, use_skycoord=True, marker_name='my_markers')

If you have a large catalog, you might want to filter your table to the
marks of interest before adding them to Imviz, in order to avoid performance
issues associated with adding large numbers of markers. For instance, if your
image has FITS WCS, you could use `astropy.wcs.WCS.footprint_contains` if you
only want the marks within a footprint. Alternately, you could filter by
relevant columns in your catalogs, such as brightness, distance, etc.

And to remove those markers:

.. code-block:: python

    viewer.remove_markers(marker_name='my_markers')

.. _imviz-import-regions-api:

Importing regions via the API
=============================

If you have a region file supported by :ref:`regions:regions_io`, you
can load the regions into Imviz as follows:

.. code-block:: python

    imviz.load_regions_from_file("/path/to/data/myregions.reg")

Unsupported regions will be skipped and trigger a warning. Those that
failed to load, if any, can be returned as a list of tuples of the
form ``(region, reason)``:

.. code-block:: python

    bad_regions = imviz.load_regions_from_file("/path/to/data/myregions.reg", return_bad_regions=True)

For more details on the API, please see
:meth:`~jdaviz.core.helpers.ImageConfigHelper.load_regions_from_file`
and :meth:`~jdaviz.core.helpers.ImageConfigHelper.load_regions` methods
in Imviz.
