.. _mosviz-redshift:

*******************
Setting Redshift/RV
*******************

The :ref:`Line Lists Plugin <mosviz-line-lists>` contains a redshift slider as well as the ability to 
view and set the redshift and/or radial velocity.

From the notebook
=================

In the notebook, the value of the Redshift column can be changed for all rows or a single row
using :meth:`~jdaviz.configs.mosviz.helper.Mosviz.update_column`.

The 1D and 2D spectrum objects can be retrieved (with redshift optionally applied) using
:meth:`~jdaviz.configs.mosviz.helper.Mosviz.get_spectrum_1d` and :meth:`~jdaviz.configs.mosviz.helper.Mosviz.get_spectrum_2d`,
respectively.
