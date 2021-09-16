***********************************
Import Data From Notebook to Jdaviz
***********************************

..
    Specific instructions on exporting data from Jdaviz to your notebook vary slightly for each instance of Jdaviz, including :ref:`specviz-import_data`, :ref:`cubeviz-import_data`, :ref:`mosviz-import_data`, and Imviz.

Specific instructions on exporting data from Jdaviz to your notebook vary slightly for each instance of Jdaviz, including for :ref:`Specviz <api-import>`, :ref:`Cubeviz <api-import-cubeviz>`, :ref:`Mosviz <mosviz-import-data>`, and :ref:`Imviz <imviz-import-data>`.  These instructions
all provide the ability to import data with the GUI or the API via the Jupyter notebook.

If using the Jupyter notebook, users can load data into the application through code using the ``load_data``
method, which takes as input either the name of a local file or a
:class:`~spectral_cube.SpectralCube` or :class:`~specutils.Spectrum1D` object.

For Specviz::

    from jdaviz import Specviz
    from specutils import Spectrum1D
    specviz = Specviz()
    specviz.app
    spec1d = Spectrum1D.read("/path/to/data/spectrum_file.fits")
    specviz.load_data(spec1d)

If you need to create your own `~specutils.Spectrum1D` file::

    from specutils import Spectrum1D
    flux = np.random.randn(200) * u.Jy
    wavelength = np.arange(5100, 5300) * u.AA
    spec1d = Spectrum1D(spectral_axis=wavelength, flux=flux)

For Cubeviz::

    from jdaviz import Cubeviz
    cubeviz = Cubeviz()
    cubeviz.app
    cubeviz.load_data("/path/to/data/cube_file.fits")

For Mosviz::

    from jdaviz import Mosviz
    mosviz = Mosviz()
    mosviz.app
    mosviz.load_data(directory="/path/to/data", instrument="nirspec")  # Or "niriss"

For Imviz::

    from jdaviz import Imviz
    imviz = Imviz()
    imviz.app
    imviz.load_data("/path/to/data/image.fits")
