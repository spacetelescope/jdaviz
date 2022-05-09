.. image:: ../logos/imviz.svg
   :width: 400

.. _imviz:

#####
Imviz
#####

Imviz is a tool for visualization and quick-look analysis for 2D astronomical
images. Like the rest of Jdaviz, it is written in the Python programming
language, and therefore can be run anywhere Python is supported
(see :doc:`../installation`). Imviz is built on top of the
`Glupyter <https://glue-jupyter.readthedocs.io>`_ backend, providing a visual,
interactive interface to the analysis capabilities in that library.


Quickstart
----------

To load a sample `HST/ACS Image <https://mast.stsci.edu/api/v0.1/Download/file?uri=mast:HST/product/jbqf03gjq_flc.fits>`_ into ``Imviz`` in the standalone app, run::

    jdaviz imviz /path/to/jbqf03gjq_flc.fits


Or to load in a Jupyter notebook, see the :gh-notebook:`ImvizExample`.


Using Imviz
-----------

.. toctree::
  :maxdepth: 2

  import_data
  displayimages
  plugins
  notebook
