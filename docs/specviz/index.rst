.. |specviz_logo| image:: ../logos/specicon.svg
    :height: 42px

.. _specviz:

######################
|specviz_logo| Specviz
######################

.. image:: https://stsci.box.com/shared/static/qlrlsf12fl9v9wjy321hwrjk8d9jf5h8.gif
    :alt: Introductory video tour of the Specviz configuration and its features

Specviz is a tool for visualization and quick-look analysis of 1D astronomical spectra.
It incorporates visualization tools with analysis capabilities,
such as Astropy regions and :ref:`specutils` packages.
Users can interact with their data from within the tool.

Specviz allows spectra to be easily plotted and examined.
It supports flexible spectral unit conversions, custom plotting attributes,
interactive selections, multiple plots, and other features.
Specviz notably includes a measurement tool for spectral lines which enables
the user, with a few mouse actions, to perform and record measurements.
It has a model fitting capability that enables the user to create simple
(e.g., single Gaussian) or multi-component models
(e.g., multiple Gaussians for emission and absorption lines in addition
to regions of flat continua).

A typical data-analysis workflow might involve
data exploration using Specviz and then scripting to create more
complex measurements or modeling workflows using specutils.
Data can be both imported into and exported out of the tool so
users can continue their desired workflow within the notebook.
This documentation provides details on its various capabilities alongside demo
videos and example notebooks.

.. We do not want a real section here so navbar shows toc directly.

**Using Specviz**

.. toctree::
  :maxdepth: 2

  import_data
  displaying
  plugins
  export_data
  examples
