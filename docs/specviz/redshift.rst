.. _specviz-redshift:

*******************
Setting Redshift/RV
*******************

The :ref:`Line Lists Plugin <line-lists>` contains a redshift slider as well as the ability to 
view and set the redshift and/or radial velocity.

Additionally, the :ref:`Line Analysis Plugin <line-analysis>` includes the capability to 
compute and assign the redshift based on the measured centroid of a line.

From the notebook
=================

The range of the slider, as well as the resolution of a single
step in the slider, can be set from a notebook cell using the 
:meth:`~jdaviz.configs.default.plugins.line_lists.line_list_mixin.LineListMixin.set_redshift_slider_bounds`
method in ``specviz`` by specifying the ``range`` and/or ``step`` keywords.  By setting either or both
of these to 'auto', they will default based on the x-limits of the spectrum plot.

The redshift itself can be set from the notebook using the ``set_redshift`` method.

Any set redshift values are applied to spectra output using the
:meth:`jdaviz.configs.specviz.helper.Specviz.get_spectra` helper method.
Note that using the lower-level app data retrieval (e.g.,
``specviz.app.get_data_from_viewer()``) will return the data as
originally loaded, with the redshift unchanged. 
