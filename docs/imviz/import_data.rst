.. _imviz-import-data:

*************************
Importing Data into Imviz
*************************

Imviz can load data in the form of a filename (FITS, JPEG, or PNG),
an `~astropy.nddata.NDData` object, or a NumPy array if the data is 2D.
See :meth:`jdaviz.configs.imviz.helper.Imviz.load_data` for more information.

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

Once data is loaded, you may use the :guilabel:`Import Data` button again
to load regions from a ``.reg`` file; also see :ref:`imviz-import-regions-api`.

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

If you have a `stdatamodels.datamodels <https://stdatamodels.readthedocs.io/en/latest/jwst/datamodels/index.html#data-models>`_
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

Roman datamodels
----------------

You can also load Nancy Grace Roman Space Telescope (hereafter, Roman) data products, which are
provided as ASDF files. If an ASDF file has a ``roman`` attribute, Jdaviz will
open it with `roman-datamodels <https://github.com/spacetelescope/roman_datamodels>`_.
You must run ``pip install roman-datamodels`` separately as it is not automatically installed
by Jdaviz.

.. code-block:: python

    from jdaviz import Imviz

    imviz = Imviz()
    imviz.load_data("WFI01_cal.asdf")
    imviz.show()

.. _imviz-import-catalogs-api:

Batch Loading Multiple Images
-----------------------------

To save on performance while loading multiple images into Imviz, you can optionally use
:meth:`~jdaviz.core.helpers.ConfigHelper.batch_load` to parse all of the data first (within a for
loop or multiple calls to ``load_data``, for example), and defer the linking and loading of the new
data entries into the viewer until after the parsing is complete::

    from jdaviz import Imviz
    imviz = Imviz()
    with imviz.batch_load():
        for filepath in filepaths:
            imviz.load_data(filepaths)
    imviz.show()


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

You could also define :ref:`regions:shapes` programmatically and load them; e.g.:

.. code-block:: python

    from regions import CirclePixelRegion, PixCoord
    aper_1 = CirclePixelRegion(center=PixCoord(x=42, y=43), radius=4.2)
    aper_2 = CirclePixelRegion(center=PixCoord(x=10, y=20), radius=3)
    imviz.load_regions([aper_1, aper_2])

For more details on the API, please see
:meth:`~jdaviz.core.helpers.ImageConfigHelper.load_regions_from_file`
and :meth:`~jdaviz.core.helpers.ImageConfigHelper.load_regions` methods
in Imviz.
