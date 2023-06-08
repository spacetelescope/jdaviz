.. |cubeviz_logo| image:: ../logos/cube.svg
    :height: 42px

.. _cubeviz:

######################
|cubeviz_logo| Cubeviz
######################

.. image:: https://stsci.box.com/shared/static/esod50xtbn07wvls1ia07urnr65tv2bj.gif
    :alt: Introductory video tour of the Cubeviz configuration and its features

Cubeviz is a visualization and analysis toolbox for data cubes from
integral field units (IFUs). It is built as part of the
`Glue visualization <https://glueviz.org>`_ tool. Cubeviz is designed to work
with data cubes from the NIRSpec and MIRI instruments on JWST, and will work
with IFU data cubes. It uses
the `specutils <https://specutils.readthedocs.io/en/latest/>`_ package
from `Astropy <https://www.astropy.org>`_ .

Cubeviz is a tool for visualization and quick-look analysis of 3D data cubes,
primarily from integral field units (IFUs). It incorporates visualization tools
with analysis capabilities, such as Astropy regions and :ref:`specutils` packages.
Users can interact with their data from within the tool.
Cubeviz allows spectra of regions within the cube to be easily plotted and examined,
offering all the same capabilities as :ref:`specviz`.

In addition, Cubeviz also allows users to interacting with their cube to:

* view the wavelength slices (RA, DEC),

* view flux, error, and data quality cubes simultaneously,

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

.. We do not want a real section here so navbar shows toc directly.

**Using Cubeviz**

.. toctree::
  :maxdepth: 2

  import_data
  displaycubes
  displayspectra
  plugins
  export_data
  examples
