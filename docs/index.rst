######
Jdaviz
######

.. grid:: 3
   :gutter: 1

   .. grid-item-card::
      :img-top: logos/imviz\ icon.svg

      .. button-ref:: imviz/index
         :expand:
         :color: primary
         :click-parent:

         Jump to Imviz

   .. grid-item-card::
      :img-top: logos/specicon.svg

      .. button-ref:: specviz/index
         :expand:
         :color: primary
         :click-parent:

         Jump to Specviz

   .. grid-item-card::
      :img-top: logos/cube.svg

      .. button-ref:: cubeviz/index
         :expand:
         :color: primary
         :click-parent:

         Jump to Cubeviz

   .. grid-item-card::
      :img-top: logos/specviz2d\ icon.svg

      .. button-ref:: specviz2d/index
         :expand:
         :color: primary
         :click-parent:

         Jump to Specviz2D

   .. grid-item-card::
      :img-top: logos/mos.svg

      .. button-ref:: mosviz/index
         :expand:
         :color: primary
         :click-parent:

         Jump to Mosviz

``jdaviz`` is a package of astronomical data analysis visualization
tools based on the Jupyter platform.  These GUI-based tools link data
visualization and interactive analysis.  They are designed to work
within a Jupyter notebook cell, as a standalone desktop application,
or as embedded windows within a website -- all with nearly identical
user interfaces.

``jdaviz`` applications currently include tools for interactive
visualization of spectroscopic and imaging data.
:ref:`imviz` is a tool for visualization and quick-look analysis for 2D astronomical images.
:ref:`specviz` is a tool for visualization and quick-look analysis of 1D astronomical spectra.
:ref:`cubeviz` provides a view of spectroscopic data cubes (like those
to be produced by JWST MIRI), along with 1D spectra extracted from the
cube.
:ref:`mosviz` is a visualization tool for many astronomical
spectra, typically the output of a multi-object spectrograph (e.g.,
JWST NIRSpec), and includes viewers for 1D and 2D spectra as well as
contextual information like on-sky views of the spectrograph slit.

.. warning::

   As of ``jdaviz`` version 3.5, python 3.8 is no longer supported. Please use python 3.9 or
   greater to get the latest bug fixes and feature additions for ``jdaviz``.

.. note::

   ``jdaviz`` is one tool that is part of STScI's larger
   `Data Analysis Tools Ecosystem <https://jwst-docs.stsci.edu/jwst-post-pipeline-data-analysis>`_.

.. note::

   The offline version of this documentation can be downloaded from
   `Jdaviz zipped HTML downloads page <https://readthedocs.org/projects/jdaviz/downloads/>`_.

.. note::

   Recordings and instructional notebooks from live Jdaviz tutorials can be found at
   `the JWebbinar website <https://www.stsci.edu/jwst/science-execution/jwebbinars>`_
   under the "Materials and Videos" expandable section. Scroll down to the bottom of that section
   to find materials from the most recent session (JWebbinar 24, March 2023).

************
Using Jdaviz
************

.. toctree::
  :maxdepth: 2

  index_using_jdaviz

*******************************
JWST Instrument Modes in Jdaviz
*******************************

.. toctree::
  :maxdepth: 2

  index_jwst_modes

*****************
Development Guide
*****************

.. toctree::
   :maxdepth: 2

   index_ref_api

*********************
License & Attribution
*********************

.. toctree::
   :maxdepth: 2

   index_citation
