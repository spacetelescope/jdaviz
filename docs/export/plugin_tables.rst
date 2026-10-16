.. _export-plugin_tables:
.. rst-class:: section-icon-mdi-content-save

*************
Plugin Tables
*************

Several plugins produce tables that can be exported:

- back into your Jupyter notebook,
- as a file.


Supported Formats
=================

Subsets can be exported as:

- ECSV 

API Access
==========

.. code-block:: python

   plg = jd.plugins['Export']
   plg.table = 'Plugin Name: table'
   plg.filename = 'my-subset'
   plg.export()


UI Access
=========

.. guidestar-demo:: _static/jdaviz-wireframe.html
   :repeat: false
   :init-steps-json: [{"action":"disable-toolbar-except","value":"save"}]
   :steps-json: [{"action": "show-sidebar", "value": "save", "delay": 1500, "caption": "Open the export sidebar"}]

.. _plugin_table_toplevelapi:

Top-Level API Access
====================

To access plugin tables in a Jupyter notebook, you can export the tables by directly calling the plugin:

.. code-block:: python 

   regions = jdaviz.plugins["Aperture Photometry"].export_table()

This returns a :class:`~astropy.table.QTable` for the given plugin table.  


Aperture Photometry
===================

If you opted to fit a `~astropy.modeling.functional_models.Gaussian1D`
to the radial profile, the last fitted model parameters will be displayed
under the radial profile plot. The model itself can be obtained as follows.
See :ref:`astropy:astropy-modeling` on how to manipulate the model:

.. code-block:: python

    ap_phot = jdaviz.plugins['Aperture Photometry']
    my_gaussian1d = ap_phot.fitted_models['phot_radial_profile']

The bottom of the plugin shows a table of past results, along with the subset
and data used to compute them.  These results can be exported as an `~astropy.table.QTable` 
as in :ref:`plugin_table_toplevelapi`.

The output table contains the results you see in the plugin and then some.
The columns are as follow:

* :attr:`~photutils.aperture.ApertureStats.id`: ID number assigned to the row,
  starting from 1.
* ``xcenter``, ``ycenter``: Center of the aperture (0-indexed).
* ``sky_center``: `~astropy.coordinates.SkyCoord` associated with the center.
  If WCS is not available, this field is `None`.
* ``background``: The value from :guilabel:`Background value`, with unit attached.
* :attr:`~photutils.aperture.ApertureStats.sum`: Sum of flux in the aperture.
  If per steradian is in input data unit, total pixel area covered in steradian
  is already multiplied here, if applicable, so there will be no per steradian
  in its unit. Otherwise, it has the same unit as input data. For more details
  on how the photometry is done, see :ref:`photutils:photutils-aperture`.
* :attr:`~photutils.aperture.ApertureStats.sum_aper_area`: The pixel area
  covered by the region. Partial coverage is reported as fraction.
* ``pixarea_tot``: If per steradian is in input data unit and pixel area is
  provided, this contains the conversion factor for the *sum* to take out
  the steradian unit. Otherwise, it is `None`.
* ``aperture_sum_counts``: This is the aperture sum converted to counts,
  if :guilabel:`Counts conversion factor` was set. Otherwise, it is `None`.
  This calculation is done without taking account of ``pixarea_tot``, even
  when it is available.
* ``aperture_sum_counts_err``: This is the Poisson uncertainty (square root)
  for ``aperture_sum_counts``. Other uncertainty factors like readnoise are
  not included. In the plugin, it is displayed within parenthesis next to
  the value for ``aperture_sum_counts``, if applicable.
* ``counts_fac``: The value from :guilabel:`Counts conversion factor`, with
  unit attached, if applicable. Otherwise, it is `None`.
* ``aperture_sum_mag``: This is the aperture sum converted to magnitude, if
  :guilabel:`Flux scaling` was set. Otherwise, it is `None`. This calculation
  is done without taking account of ``pixarea_tot``, even when it is available.
* ``flux_scaling``: The value from :guilabel:`Flux scaling`, with unit attached,
  if applicable. Otherwise, it is `None`.
* :attr:`~photutils.aperture.ApertureStats.min`,
  :attr:`~photutils.aperture.ApertureStats.max`,
  :attr:`~photutils.aperture.ApertureStats.mean`,
  :attr:`~photutils.aperture.ApertureStats.median`,
  :attr:`~photutils.aperture.ApertureStats.mode`,
  :attr:`~photutils.aperture.ApertureStats.std`,
  :attr:`~photutils.aperture.ApertureStats.mad_std`,
  :attr:`~photutils.aperture.ApertureStats.var`,
  :attr:`~photutils.aperture.ApertureStats.biweight_location`,
  :attr:`~photutils.aperture.ApertureStats.biweight_midvariance`: Basic statistics
  from the aperture.
* :attr:`~photutils.aperture.ApertureStats.fwhm`,
  ``semimajor_axis`` (or ``semimajor_sigma`` for Photutils <3),
  ``semiminor_axis`` (or ``semiminor_sigma`` for Photutils <3),
  :attr:`~photutils.aperture.ApertureStats.orientation`,
  :attr:`~photutils.aperture.ApertureStats.eccentricity`: Properties of a 2D
  Gaussian function that has the same second-order central moments as the source.
* ``data_label``: Data label of the image used.
* ``slice_wave``: The wavelength value at the selected slice of a cube. Will be NaN for 2D data. 
* ``subset_label``: Subset label of the region used.
* ``timestamp``: Timestamp of when the photometry was performed as
  `~astropy.time.Time`.

.. note::

    Aperture sum and statistics are done on the originally drawn aperture only.
    You can use the :ref:`subsets` plugin to center it first on the
    object of interest, if you wish.

Once you have the results in a table, you can further manipulated them as
documented in :ref:`astropy:astropy-table`.

.. _plugin_tables_export-model:

Model Fits
==========

For a list of model labels:

.. code-block:: python

    models = jdaviz.plugins['Model Fitting'].get_models()
    models

Once you know the model labels, to get a specific model:

.. code-block:: python

    mymodel = jdaviz.plugins['Model Fitting'].get_models(model_label="ModelLabel")

To extract all of the model parameters:

.. code-block:: python

    myparams = jdaviz.plugins['Model Fitting'].get_model_parameters(model_label="ModelLabel")
    myparams

where the ``model_label`` parameter identifies which model should be returned.

Alternatively, the table of logged parameter values in the model fitting plugin can be exported to
an :ref:`astropy table <astropy:astropy-table>`
by calling :meth:`~jdaviz.core.template_mixin.TableMixin.export_table` (see :ref:`plugin-apis`):

.. code-block:: python

    model_fitting = jdaviz.plugins['Model Fitting']
    model_fitting.export_table()


.. _plugin_tables_export-markers:

Markers Table
=============

All mouseover information in the :ref:`markers plugin <info-markers>` can be exported to an
:ref:`astropy table <astropy:astropy-table>`
by calling :meth:`~jdaviz.core.template_mixin.TableMixin.export_table` (see :ref:`plugin-apis`):

.. code-block:: python

    markers_plugin = jdaviz.plugins["Markers"]
    markers_table = markers_plugin.export_table()

.. _plugin_tables_export-distance:

Distance Table
==============

All mouseover information in the :ref:`distance tool <distance-tool>` can be exported to an
:ref:`astropy table <astropy:astropy-table>`
by calling :meth:`~jdaviz.core.template_mixin.TableMixin.export_table` (see :ref:`plugin-apis`):

.. code-block:: python

    markers_plugin = jdaviz.plugins["Markers"]
    markers_table = markers_plugin.measurements_table.export_table()


