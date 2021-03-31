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
