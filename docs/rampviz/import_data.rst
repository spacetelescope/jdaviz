.. _rampviz-import-api:

***************************
Importing Data into Rampviz
***************************


Level 1 ramp products can be loaded into Rampviz with
:py:meth:`~jdaviz.configs.rampviz.helper.Rampviz.load_data`. Rampviz loads
Level 1 ramp cubes from:

- JWST when given as paths to "_uncal.fits" files
  or :py:class:`~stdatamodels.jwst.datamodels.Level1bModel` data models, or

- Roman Level 1 ramp files in asdf format or
  :py:class:`~roman_datamodels.datamodels.RampModel` data models.

In order to load Roman files, you will need to install the :ref:`optional-deps-roman`.

