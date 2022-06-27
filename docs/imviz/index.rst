.. image:: ../logos/imviz.svg
   :width: 400

.. _imviz:

#####
Imviz
#####

.. image:: ../img/landing_gifs/Imviz_landing.gif
    :alt: Introductory video tour of the Imviz configuration and its features

Imviz is a tool for visualization and analysis of 2D astronomical images.
It incorporates visualization tools with analysis capabilities, such as Astropy
regions and photutils packages.
Users can interact with their data from within the tool.
Imviz also provides programmatic access to its viewers using
`Astrowidgets <https://astrowidgets.readthedocs.io/en/latest/>`_ API;
see `~jdaviz.core.astrowidgets_api.AstrowidgetsImageViewerMixin` for available functionality.
Data can be both imported into and exported out of the tool so users can continue their
desired workflow within the notebook.
This documentation provides details on the various capabilities, demo videos, and example notebooks.

.. toctree::
  :maxdepth: 2

  import_data
  displayimages
  plugins
  export_data
  examples
