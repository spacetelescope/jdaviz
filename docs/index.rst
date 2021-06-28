######
Jdaviz
######

.. image:: logos/jdaviz.svg
   :width: 400

.. note::

   ``Jdaviz`` is one tool that is part of STScI's larger `Data Analysis Tools Ecosystem <https://jwst-docs.stsci.edu/jwst-post-pipeline-data-analysis>`_.


``Jdaviz`` is a package of astronomical data analysis visualization
tools based on the Jupyter platform.  These GUI-based tools link data
visualization and interactive analysis.  They are designed to work
within a Jupyter notebook cell, as a standalone desktop application,
or as embedded windows within a website -- all with nearly-identical
user interfaces.

``jdaviz`` applications currently include tools for interactive
visualization of spectroscopic data.  SpecViz is a tool for
visualization and quick-look analysis of 1D astronomical spectra.
MOSViz is a visualization tool for many astronomical spectra,
typically the output of a multi-object spectrograph (e.g., JWST
NIRSpec), and includes viewers for 1D and 2D spectra as well as
contextual information like on-sky views of the spectrograph slit.
Cubeviz provides a view of spectroscopic data cubes (like those to be
produced by JWST MIRI), along with 1D spectra extracted from the cube.

.. _jdaviz_instrument_table:

JWST Instrument Modes in Jdaviz
===============================

This tool is designed with instrument modes from the James Webb Space Telescope (JWST) in mind, but
the tool should be flexible enough to read in data from many astronomical telescopes.  The table below
summarizes Jdaviz file support specific to JWST instrument modes.

.. list-table:: JWST Instrument Modes in Jdaviz
   :widths: 25 15 10 15 20
   :header-rows: 1

   * - Instrument
     - Template Mode
     - File Type
     - Pipeline Level
     - Primary Configuration
   * - NIRSpec
     - MOS
     - S2D
     - 2b,3
     - Mosviz
   * -
     -
     - X1D
     - 2b,3
     - Specviz
   * -
     - IFU
     - S3D
     - 2b,3
     - Cubeviz
   * -
     -
     - X1D
     - 2b,3
     - Specviz
   * -
     - FS
     - S2D
     - 2b,3
     - Specviz2d
   * -
     -
     - X1D
     - 2b,3
     - Specviz
   * -
     - BOTS
     - X1DINTS
     - --
     - No Support
   * - NIRISS
     - IMAGING
     - I2D
     - 2b,3
     - Imviz
   * -
     - WFSS
     - X1D
     - 2b
     - Specviz
   * -
     - AMI
     - AMINORM
     - --
     - No Support
   * -
     - SOSS
     - X1DINTS
     - --
     - No Support
   * - NIRCam
     - Imaging
     - I2D
     - 2b,3
     - Imviz
   * -
     - Coronagraphic Imaging
     - I2D
     - 2b,3
     - Imviz
   * -
     - WFSS
     - X1D
     - 2b
     - Specviz
   * -
     - Grism TSO
     - X1DINTS
     - --
     - No Support
   * - MIRI
     - Imaging
     - I2D
     - 2b,3
     - Imviz
   * -
     - Coronagraphic Imaging
     - I2D
     - 2b,3
     - Imviz
   * -
     - LRS-slit
     - S2D
     - 2b,3
     - Specviz2d
   * -
     -
     - X1D
     - 2b,3
     - Specviz
   * -
     - LRS-slitless
     - X1DINTS
     - --
     - No Support
   * -
     - MRS
     - S3D
     - 2b,3
     - Cubeviz
   * -
     -
     - X1D
     - 2b, 3
     - Specviz


Using Jdaviz
============

.. toctree::
  :maxdepth: 2

  installation.rst
  quickstart.rst
  specviz/index.rst
  cubeviz/index.rst
  mosviz/index.rst
  imviz/index.rst

Reference/API
=============

.. toctree::
   :maxdepth: 2

   dev/index.rst
   reference/api.rst

Additional documentation
========================

.. toctree::
   :maxdepth: 1

   known_bugs.rst
