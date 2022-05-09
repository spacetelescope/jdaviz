
.. image:: ../logos/cubeviz.svg
   :width: 400

.. _cubeviz:

#######
Cubeviz
#######

Cubeviz is a visualization and analysis toolbox for data cubes from integral field units (IFUs). It is built as part of the `Glue visualization <https://glueviz.org>`_ tool. Cubeviz is designed to work with data cubes from the NIRSpec and MIRI instruments on JWST, and will work with IFU data cubes. It uses the `specutils <https://specutils.readthedocs.io/en/latest/>`_ package from `Astropy <https://www.astropy.org>`_ .

The core functionality of Cubeviz currently includes the ability to:

* view the wavelength slices (RA, DEC) in a data cube,

* view flux, error, and data quality slices simultaneously,

* view spectra from selected spatial (RA, DEC) regions,

* smooth cubes spatially (RA, DEC) and spectrally (wavelength),

* create and display contour maps,

* collapse cubes over selected wavelength regions,

* fit spectral lines,

* create moment maps, including line flux and kinematic maps (rotation velocity and velocity dispersion),

* overlay spectral line lists,

* save edited cubes,

* save figures,

* fit models to every spaxel

Future functionality will include the ability to:

* save and restore a session,


* create RGB images from regions collapsed in wavelength space (i.e., linemaps),

* output python scripts for making figures,

* output astropy commands,

* match spatial resolution among selected data cubes,

* bin data into constant signal-to-noise regions

Quickstart
----------

To load a sample `SDSS MaNGA IFU data cube <https://stsci.box.com/shared/static/28a88k1qfipo4yxc4p4d40v4axtlal8y.fits>`_ into ``Cubeviz`` in the standalone app, run::

    jdaviz cubeviz /path/to/manga-7495-12704-LOGCUBE.fits


Or to load in a Jupyter notebook, see the :gh-notebook:`CubevizExample`.

Using Cubeviz
-------------

.. toctree::
  :maxdepth: 2

  import_data
  displaycubes
  displayspectra
  plugins
  notebook
