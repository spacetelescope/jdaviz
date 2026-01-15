.. _imviz-import-data:

*************************
Importing Data into Imviz
*************************

.. include:: ../_templates/deprecated_config_banner.rst

Imviz can load data in the form of a filename (FITS, JPEG, or PNG),
an `~astropy.nddata.NDData` object, or a NumPy array if the data is 2D.
See :py:meth:`~jdaviz.configs.imviz.helper.Imviz.load` for more information.

.. note::

    Loading too many datasets will cause performance problems due to
    the number of links necessary; see :ref:`glueviz:linking-framework`
    for more information.

.. _imviz-import-commandline:

Importing data through the Command Line
=======================================

When running the Imviz application via the command line, you may provide a path
to a compatible file, which will be loaded into the app on initialization.
Multiple data files may be provided:

.. code-block:: bash

    jdaviz --layout=imviz /my/image/data1.fits /my/image/data2.fits

.. _imviz-import-gui:

Importing data through the UI
=============================

You can load your data into the Imviz application
by clicking the :guilabel:`Import Data` button at the top left of the application's
user interface. This opens a dialogue where the user can select a file
that can be parsed as a :class:`~astropy.nddata.NDData`, :class:`~astropy.io.fits.HDUList`,
or :class:`~astropy.io.fits.ImageHDU` in the text field.

After clicking :guilabel:`Import`, the data file will be parsed and loaded into the
application. A notification will appear to let users know if the data import
was successful. Afterward, the new data set can be found in the :guilabel:`Data`
tab of each viewer's options menu as described in :ref:`cubeviz-selecting-data`.

Once data is loaded, you may use the :guilabel:`Import Data` button again
to load regions from a ``.reg`` file; also see :ref:`imviz-import-regions-api`.

.. _imviz-import-api:

Downloading data products through the Virtual Observatory
---------------------------------------------------------
Imviz supports querying and loading data products from `IVOA's Virtual Observatory <https://ivoa.net/>`_.
The plugin will search for registered archives with observations that intersect the circular field
specified by the user.

To search the VO, enter a source location and a radius around which to search. The source utilizes
:class:`~astropy.coordinates.SkyCoord`'s resolver and can accept a common source name (e.g. Messier or NGC) or
any string representations of astronomical coordinates understood by ``SkyCoord``. For more information,
see :ref:`astropy:astropy-coordinates-high-level`. If a radius is not provided, a circular field of 1 degree
centered on the source will be assumed.

By default, the plugin will limit results to archives which report coverage intersecting the provided cirular
field. To instead see all available archives on the IVOA registry, toggle the :guilabel:`Filter by Coverage` button.

.. note::

    Some archives have not provided coverage information, and thus will be excluded from the results.
    If you are expecting an archive that does not appear, try disabling coverage filtering.

Additionally, select the corresponding waveband of the archive you are looking for;
this will limit the query to
archives and services within your specified wavelength range.
Waveband definitions can be
found `here <https://wiki.ivoa.net/internal/IVOA/IvoaUCD/NoteEMSpectrum-20040520.html>`_.

After selecting the waveband, the plugin will query the VO registry for services that match the provided criteria.
If coverage filtering is enabled, only archives and surveys that report coverage within the user's specified area
will be reported. Otherwise, the list will return all available archives and surveys in that waveband. Select your
resource to query and press the :guilabel:`Query Archive` button to search your specified archive with your
specific target.

Once the query is complete, the table of results will be populated with the archive provided ``Title``,
``Date``, and ``Instrument`` of each result. Select your desired data products to load and click
:guilabel:`Load Data` to download and import your selected data products to Imviz.

.. note::

    Currently only `Simple Image Access specification (SIA) 1.0 <https://www.ivoa.net/documents/WD/SIA/sia-20040524.html#:~:text=Simple%20Image%20Access%20Specification%20Version,Image%20Generation>`_
    services are implemented. VO services which offer only SIA2 endpoints are not supported.

.. _imviz-virtual-observatory:

Importing data via the API
==========================

Alternatively, users who work in a coding environment like a Jupyter
notebook can access the Imviz helper class API. Using this API, users can
load data into the application through code with the
:py:meth:`~jdaviz.configs.imviz.helper.Imviz.load`
method, which takes as input either the name of a local file, 2D NumPy array, or an
:class:`~astropy.nddata.NDData`, :class:`~astropy.io.fits.HDUList`,
or :class:`~astropy.io.fits.ImageHDU` object.

For more information on loading data, see :ref:`import-data`.

FITS Files
----------

The example below loads the first science extension of the given FITS file into Imviz:

.. code-block:: python

    from jdaviz import Imviz
    imviz = Imviz()
    imviz.load('/path/to/data/image.fits', format='Image')
    imviz.show()

Creating Your Own Array
-----------------------

You can create your own array to load into Imviz:

.. code-block:: python

    import numpy as np
    from jdaviz import Imviz

    arr = np.arange(100).reshape((10, 10))
    imviz = Imviz()
    imviz.load(arr, format='Image', data_label='my_array')
    imviz.show()

JWST datamodels
---------------

If you have a `stdatamodels.datamodels <https://stdatamodels.readthedocs.io/en/latest/jwst/datamodels/index.html#data-models>`_
object, you can load it into Imviz as follows:

.. code-block:: python

    from astropy.nddata import NDData, StdDevUncertainty
    from jdaviz import Imviz

    # mydatamodel is a jwst.datamodels object with stddev ERR array
    ndd = NDData(mydatamodel.data,
                 uncertainty=StdDevUncertainty(mydatamodel.err),
                 mask=mydatamodel.dq,
                 wcs=mydatamodel.meta.wcs,
                 meta=dict(mydatamodel.meta.items()))
    imviz = Imviz()
    imviz.load(ndd, format='Image', data_label='my_data_model')
    imviz.show()

Roman datamodels
----------------

You can also load Nancy Grace Roman Space Telescope (hereafter, Roman) data products, which are
provided as ASDF files. If an ASDF file has a ``roman`` attribute, Jdaviz will
open it with `roman-datamodels <https://github.com/spacetelescope/roman_datamodels>`_.
In order to load Roman files, you will need to install the :ref:`optional-deps-roman`.

.. code-block:: python

    from jdaviz import Imviz

    imviz = Imviz()
    imviz.load("WFI01_cal.asdf", format='Image')
    imviz.show()

.. _imviz-import-catalogs-api:

Batch Loading Multiple Images
-----------------------------

To save on performance while loading multiple images into Imviz, you can optionally use the
:meth:`~jdaviz.core.helpers.ConfigHelper.batch_load` context manager to parse all of the data first (within a
loop, for example, or multiple calls to ``load``), and defer the linking and loading of the new
data entries into the viewer until after the parsing is complete::

    from jdaviz import Imviz
    imviz = Imviz()
    with imviz.batch_load():
        for filepath in filepaths:
            imviz.load(filepath, format='Image')
    imviz.show()


.. _load-data-uri:

Load data from a URI or URL
---------------------------

The examples above import data from a local file path, and also support loading remote
data from a URL or URI with :py:meth:`~jdaviz.configs.imviz.helper.Imviz.load`.
If the input is a string with a MAST URI, the file will be retrieved via
astroquery's `~astroquery.mast.ObservationsClass.download_file`. If the
input string is a URL, it will be retrieved via astropy with
`~astropy.utils.data.download_file`. Both methods support a
``cache`` argument, which will store the file locally. Cached downloads via astropy
are placed in the :ref:`astropy cache <astropy:utils-data>`,
and URIs retrieved via astroquery can be saved to a path of your choice with
``local_path``. If the ``cache`` argument hasn't been set, the file will be cached
and a warning will be raised.

Local file URIs beginning with ``file://``
are not supported by this method – nor are they necessary, since string
paths without the scheme work fine! :ref:`Cloud FITS <astropy:fits_io_cloud>` are not yet supported.

.. code-block:: python

    from jdaviz import Imviz

    uri = "mast:JWST/product/jw01345-o001_t021_nircam_clear-f200w_i2d.fits"
    cache = True

    # store the retrieved file in the current working directory:
    local_path = "jw01345-o001_t021_nircam_clear-f200w_i2d.fits"

    imviz = Imviz()
    imviz.load(uri, format='image', cache=cache, local_path=local_path)
    imviz.show()

Importing catalogs via the API
==============================

If you have a catalog file supported by `astropy.table.Table`, you
can load the catalog into Imviz and add markers to Imviz viewers to show
positions from the catalog. These markers are different than Imviz
:ref:`spatial regions <imviz-defining-spatial-regions>` as they are only meant to mark catalog positions.
Loading markers can be done with the following commands:

.. code-block:: python

    viewer = imviz.default_viewer
    viewer.marker = {'color': 'green', 'alpha': 0.8, 'markersize': 10, 'fill': False}
    my_catalog = Table.read('my_catalog.ecsv')
    coord_i2d = Table({'coord': [SkyCoord(ra=my_catalog['sky_centroid'].ra.degree,
                                          dec=my_catalog['sky_centroid'].dec.degree,
                                          unit="deg")]})
    viewer.add_markers(coord_i2d, use_skycoord=True, marker_name='my_markers')

If you have a large catalog, you might want to filter your table to the
marks of interest before adding them to Imviz to avoid performance
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

    imviz.plugins['Subset Tools'].import_region("/path/to/data/myregions.reg")

Unsupported regions will be skipped and trigger a warning. Those that
failed to load, if any, can be returned as a list of tuples of the
form ``(region, reason)`` by specifying ``return_bad_regions=True``:

.. code-block:: python

    bad_regions = imviz.plugins['Subset Tools'].import_region("/path/to/data/myregions.reg", return_bad_regions=True)

You could also define :ref:`regions:shapes` programmatically and load them; e.g.:

.. code-block:: python

    from regions import CirclePixelRegion, PixCoord
    aper_1 = CirclePixelRegion(center=PixCoord(x=42, y=43), radius=4.2)
    aper_2 = CirclePixelRegion(center=PixCoord(x=10, y=20), radius=3)
    imviz.plugins['Subset Tools'].import_region([aper_1, aper_2])
