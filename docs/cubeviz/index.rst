
.. image:: ../logos/cubeviz.svg
   :width: 400

#######
CubeViz
#######

CubeViz is an visualization and analysis toolbox for data cubes from integral field units (IFUs). It is built as part of the glue visualiztion tool. CubeViz is designed to work with data cubes from the NIRSpec and MIRI instruments on JWST, and will work with data cubes from any IFU. It uses the `specutils <https://specutils.readthedocs.io/en/latest/>`_ package from `Astropy <https://www.astropy.org>`_ .

The core functionality of CubeViz currently includes the ability to:

* view the wavelength slices (RA, DEC) in a data cube,

* view flux, error, and data quality slices simultaneously,

* view spectra from selected spatial (RA, DEC) regions,

* smooth cubes spactially (RA, DEC) and spectrally (wavelength), and

* create and display contour maps.

* collapse cubes over selected wavelength regions,

* fit spectral lines,

* create moment maps,

* perform continuum subtraction,

* cube arithmetic,

* overlay spectral line lists,

* save edited cubes,

* save figures,

* mock slit observations,

* accurate spectro-photometry,

* fit models to every spaxel

Future functionality will include the ability to:

* save and restore a session,

* create kinematic maps (rotation velocity and velocity dispersion),

* create RGB images from regions collapsed in wavelength space (i.e., linemaps),

* output python scripts for making figures,

* output astropy commands,

* match spatial resolution among selected data cubes,

* bin data into constant signal-to-noise regions

**Using CubeViz**

.. toctree::
  :maxdepth: 2

  import_data
  displaycubes
  displayspectra
  plugins
  notebook