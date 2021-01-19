
.. image:: ../logos/specviz.svg
   :width: 400

.. _specviz:

#######
Specviz
#######

Specviz is a tool for visualization and quick-look analysis of 1D astronomical spectra. Like the rest of `jdaviz`, it is written in the Python programming language, and therefore can be run anywhere Python is supported (see :doc:`../installation`). Specviz is built on top of the `specutils <https://specutils.readthedocs.io/en/latest/>`_ package from `Astropy <https://www.astropy.org>`_ , providing a visual, interactive interface to the analysis capabilities in that library.

Specviz allows spectra to be easily plotted and examined. It supports flexible spectral unit conversions, custom plotting attributes, interactive selections, multiple plots, and other features.

Specviz notably includes a measurement tool for spectral lines which enables the user, with a few mouse actions, to perform and record measurements. It has a model fitting capability that enables the user to create simple (e.g., single Gaussian) or multi-component models (e.g., multiple Gaussians for emission and absorption lines in addition to regions of flat continua). A typical data-analysis workflow might involve data exploration using SpecViz and then scripting to create more complex measurements or modeling workflows using specutils.


Using Specviz
-------------

.. toctree::
  :maxdepth: 2

  import_data
  displaying
  plugins
  redshift
  notebook
