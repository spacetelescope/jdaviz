*************************
Loading Data into Timeviz
*************************

By design, Specviz only supports data that can be parsed as
`~astropy.timeseries.TimeSeries`.

.. seealso::

    :ref:`astropy:astropy-timeseries`

Loading data via the API
------------------------

To load a Kepler time series table stored in FITS format::

    from jdaviz import Timeviz
    timeviz = Timeviz()
    timeviz.load_data('my_kepler_slc.fits', format='kepler.fits')
    timeviz.app
