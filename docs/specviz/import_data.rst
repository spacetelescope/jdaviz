***********
Import Data
***********


A user can import :class:`~specutils.Spectrum1D` data in a number of ways.

* A :class:`~specutils.Spectrum1D` object can be loaded using the Import Data button:

.. image:: img/specviz_viewer.png

Click on the "Import Data" button.

.. image:: img/import_data_1.png

Enter the path of file you would like to visualize.

.. image:: img/import_data_2.png

After you click "Import", you will then need to go to the Data Selection drop down. First, click the "hammer and screwdriver" icon to open the tool menu. Then, click the "gear" icon.

.. image:: img/import_data_3.png

Here, you can select the data you loaded to be visualized.

.. image:: img/data_selected_1.png

* A :class:`~specutils.Spectrum1D` object can also be loaded using a notebook implementation::

    >>> from jdaviz.configs.specviz.helper import SpecViz
    >>> import numpy as np
    >>> import astropy.units as u
    >>> from specutils import Spectrum1D

    >>> flux = np.random.randn(200)*u.Jy
    >>> wavelength = np.arange(5100, 5300)*u.AA
    >>> spec1d = Spectrum1D(spectral_axis=wavelength, flux=flux)
    >>> specviz = SpecViz()
    >>> specviz.load_spectrum(spec1d)


* A :class:`~specutils.Spectrum1D` object can also be loaded using a url::

    >>> # spec_url = 'https://dr14.sdss.org/optical/spectrum/view/data/format=fits/spec=lite?plateid=1323&mjd=52797&fiberid=12'
    >>> # specviz = SpecViz()
    >>> # spec = specutils.Spectrum1D.read(spec_url)


This example has the ``read`` attribute take in a url but it can also take in a file path as a parameter.
