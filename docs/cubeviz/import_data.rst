.. _cubeviz-import-data:

***************************
Importing Data into Cubeviz
***************************

By design, Cubeviz only supports data that can be parsed as
:class:`~specutils.Spectrum1D` objects. Despite the name, :class:`~specutils.Spectrum1D`
now supports 3D cubes and allows the Python-level interface and parsing tools to
be defined in ``specutils`` instead of being duplicated in Jdaviz.
:class:`~specutils.Spectrum1D` objects are very flexible in their capabilities, however,
and hence should address most astronomical spectrum use cases.

Cubeviz will automatically parse the data into the multiple viewers as described in
:ref:`cubeviz-display-cubes`. Data loaded into Cubeviz MUST contain valid WCS
keywords. For more information on how :class:`~specutils.Spectrum1D`
uses WCS, please go to the `Spectrum1D defining WCS section <https://specutils.readthedocs.io/en/stable/spectrum1d.html#defining-wcs>`_.
To check if your FITS file contains valid WCS keywords, please use
`Astropy WCS validate <astropy.wcs.validate>`.
For an example on loading a cube with valid WCS keywords, please see the :ref:`cubeviz-import-api`
section below.

.. _cubeviz-viewers:

In Cubeviz, three image viewers at the top display your data:

 |   Top Left: ``flux-viewer``
 |   Top Center: ``uncert-viewer``
 |   Top Right: ``mask-viewer``

There is also a fourth viewer called ``spectrum-viewer`` at the bottom that
will display the collapsed spectrum from ``flux-viewer``.

.. note::
    Only a single cube can be displayed in an instance of Cubeviz at a given time.
    To open a second cube, you must first initiate a second instance of Cubeviz.

.. _cubeviz-import-commandline:

Importing data through the Command Line
=======================================

You can load your data into the Cubeviz application through the command line::

    jdaviz cubeviz /my/directory/cube.fits

.. _cubeviz-import-gui:

Importing data through the GUI
==============================

Users may load data into the Cubeviz application
by clicking the :guilabel:`Import Data` button at the top left of the application's
user interface. This opens a dialogue with a prompt to select a file
that can be parsed as a :class:`~specutils.Spectrum1D` object.

After clicking :guilabel:`Import`, the data file will be parsed and loaded into the
application. A notification will appear to confirm whether the data import
was successful. Afterward, the new data set can be found in the :guilabel:`Data`
tab of each viewer's options menu as described in :ref:`cubeviz-selecting-data`.

.. _cubeviz-import-api:

Importing data via the API
==========================

Alternatively, users who work in a coding environment like a Jupyter
notebook can access the Cubeviz helper class API. Using this API, users can
load data into the application through code with the :meth:`~jdaviz.configs.specviz.helper.Specviz.load_spectrum`
method, which takes as input a :class:`~specutils.Spectrum1D` object.

FITS Files
----------
The example below loads a FITS file into Cubeviz::

    from specutils import Spectrum1D
    spec3d = Spectrum1D.read("/path/to/data/file")
    cubeviz = Cubeviz()
    cubeviz.load_data(spec3d)
    cubeviz.show()

You can also pass the path to a file that `~specutils.Spectrum1D` understands directly to the
:meth:`~jdaviz.core.helpers.ConfigHelper.load_data` method::

    cubeviz.load_data("/Users/demouser/data/cube_file.fits")
    cubeviz.show()

Creating Your Own Array
-----------------------

You can create your own array to load into Cubeviz::

    import numpy as np
    from astropy import units as u
    from astropy.wcs import WCS
    from specutils import Spectrum1D

    flux = np.arange(16).reshape((2, 2, 4)) * u.Jy
    wcs_dict = {"CTYPE1": "WAVE-LOG, "CTYPE2": "DEC--TAN", "CTYPE3": "RA---TAN",
                "CRVAL1": 4.622e-7, "CRVAL2": 27, "CRVAL3": 205,
                "CDELT1": 8e-11, "CDELT2": 0.0001, "CDELT3": -0.0001,
                "CRPIX1": 0, "CRPIX2": 0, "CRPIX3": 0}
    w = WCS(wcs_dict)

    cube = Spectrum1D(flux=flux, wcs=w)
    cubeviz.load_data(cube)
    cubeviz.show()


To then extract your data from Cubeviz, please see the :ref:`cubeviz-notebook` section.

JWST datamodels
---------------

If you have a `jwst.datamodels <https://jwst-pipeline.readthedocs.io/en/latest/jwst/datamodels/index.html>`_
object, you can load it into Imviz as follows::

    import numpy as np
    from jdaviz import Cubeviz
    import astropy.wcs as fitswcs

    # mydatamodel is a jwst.datamodels object
    # Due to current schema in jwst.datamodels, you'll need to create your own WCS object before you create your Spectrum1D object
    wcs_dict = {"CTYPE1": mydatamodel.meta.wcsinfo.ctype3, "CTYPE2": mydatamodel.meta.wcsinfo.ctype2,
            "CTYPE3": mydatamodel.meta.wcsinfo.ctype1,
            "CRVAL1": mydatamodel.meta.wcsinfo.crval3, "CRVAL2": mydatamodel.meta.wcsinfo.crval2,
            "CRVAL3": mydatamodel.meta.wcsinfo.crval1,
            "CDELT1": mydatamodel.meta.wcsinfo.cdelt3, "CDELT2": mydatamodel.meta.wcsinfo.cdelt2,
            "CDELT3": mydatamodel.meta.wcsinfo.cdelt1,
            "CRPIX1": mydatamodel.meta.wcsinfo.crpix3, "CRPIX2": mydatamodel.meta.wcsinfo.crpix2,
            "CRPIX3": mydatamodel.meta.wcsinfo.crpix1}
    my_wcs = WCS(wcs_dict)

    # Next, you need to make sure your spectral axis is the 3rd dimension
    data = mydatamodel.data * (u.MJy / u.sr)
    data = np.swapaxes(data, 0, 1)
    data = np.swapaxes(data, 1, 2)

    # Create your spectrum1
    spec3d = Spectrum1D(data, wcs = my_wcs)
    cubeviz = Cubeviz()
    cubeviz.load_spectrum(spec3d, data_label='My Cube')
    cubeviz.show()

There is no plan to natively load such objects until ``datamodels``
is separated from the ``jwst`` pipeline package.

.. _cubeviz-import-regions-api:

Importing regions via the API
=============================

If you have a region file supported by :ref:`regions:regions_io`, you
can load the regions into Cubeviz as follows::

    cubeviz.load_regions_from_file("/path/to/data/myregions.reg")

Unsupported regions will be skipped and trigger a warning. Those that
failed to load, if any, can be returned as a list of tuples of the
form ``(region, reason)``::

    bad_regions = cubeviz.load_regions_from_file("/path/to/data/myregions.reg", return_bad_regions=True)

.. note:: Sky regions are currently unsupported in Cubeviz, unlike Imviz.

For more details on the API, please see
:meth:`~jdaviz.core.helpers.ImageConfigHelper.load_regions_from_file`
and :meth:`~jdaviz.core.helpers.ImageConfigHelper.load_regions` methods
in Cubeviz.
