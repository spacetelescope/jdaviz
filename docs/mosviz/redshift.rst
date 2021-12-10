.. _mosviz-redshift:

*******************
Setting Redshift/RV
*******************

.. warning::
    Using the redshift slider with many active spectral lines can be slow, as
    every line gets replotted at each slider position. We recommended using 
    the slider with no more than around a dozen lines plotted. You can deselect
    lines using, e.g., the "Hide All" button in the line lists UI.

As in :ref:`Specviz <specviz-redshift>`, the toolbar includes a slider to adjust the redshift
or radial velocity.  In Mosviz, this is applied to the current row in the table
and is stored (and shown) in a column of the table.

From the notebook
=================

In the notebook, the value of the Redshift column can be changed for all rows or a single row
using :meth:`~jdaviz.configs.mosviz.helper.Mosviz.update_column`.

The 1D and 2D spectrum objects can be retrieved (with redshift optionally applied) using
:meth:`~jdaviz.configs.mosviz.helper.Mosviz.get_spectrum_1d` and :meth:`~jdaviz.configs.mosviz.helper.Mosviz.get_spectrum_2d`,
respectively.
