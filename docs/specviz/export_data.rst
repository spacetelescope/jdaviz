.. _specviz-export-data:

***************************
Exporting Data From Specviz
***************************

1D Spectra
==========

After data have been manipulated or analyzed, it is possible to export
those data currently back into your Jupyter notebook:

.. code-block:: python

    specviz.get_spectra()

which yields a either a single `specutils.Spectrum1D` object or a dictionary of 
`specutils.Spectrum1D` (if there are multiple displayed spectra) that you can
manipulate however you wish.  You can then load the modified spectrum back into
the notebook via the API described in :ref:`specviz-import-api`.

Alternatively, if you want more control over Specviz, you can access it the
via the ``get_data`` method of the
:py:class:`~jdaviz.configs.specviz.helper.Specviz` helper class. This method always
returns a single spectrum; if there are multiple spectra loaded you must supply a
label to the ``data_label`` argument. For example:

.. code-block:: python

    specviz.get_data(data_label='Spectrum 1')

To extract a spectrum with a spectral subset applied:

.. code-block:: python

    specviz.get_data(spectral_subset='Subset 1')

In this case, the returned `specutils.Spectrum1D` object will have a ``mask``
attribute, where ``True`` corresponds to the region outside the selected subset
(i.e., the region that has been masked out). You could load back in a copy of the
spectrum containing only your subset by running:

.. code-block:: python

    spec = specviz.get_data(spectral_subset='Subset 1')
    subset_spec = Spectrum1D(flux=spec.flux[~spec.mask],
                             spectral_axis=spec.spectral_axis[~spec.mask])
    specviz.load_data(subset_spec)

.. seealso::

    :ref:`Export From Plugins <specviz-plugins>`
        Calculations (i.e., not spectroscopic data) from the plugins can also be exported back into the Jupyter notebook in some cases.

Spectral Regions
================

If you have spectral region subsets, you can extract the parameters of these subsets
as a `specutils spectral region <https://specutils.readthedocs.io/en/stable/spectral_regions.html>`_.
For a list of available spectral regions to extract, you can type:

.. code-block:: python

    regions = specviz.get_spectral_regions()
    regions

To extract the spectral region you want:

.. code-block:: python

    myregion = regions["Subset 2"]

.. _specviz-export-model:

Model Fits
==========

For a list of model labels:

.. code-block:: python

    models = specviz.get_models()
    models

Once you know the model labels, to get a specific model:

.. code-block:: python

    mymodel = specviz.get_models(model_label="ModelLabel")

To extract all of the model parameters:

.. code-block:: python

    myparams = specviz.get_model_parameters(model_label="ModelLabel")
    myparams

where the ``model_label`` parameter identifies which model should be returned.

Alternatively, the table of logged parameter values in the model fitting plugin can be exported to
an :ref:`astropy table <astropy:astropy-table>`
by calling :meth:`~jdaviz.core.template_mixin.TableMixin.export_table` (see :ref:`plugin-apis`):

.. code-block:: python

    model_fitting = specviz.plugins['Model Fitting']
    model_fitting.export_table()


.. _specviz-export-markers:

Markers Table
=============

All mouseover information in the :ref:`markers plugin <markers-plugin>` can be exported to an
:ref:`astropy table <astropy:astropy-table>`
by calling :meth:`~jdaviz.core.template_mixin.TableMixin.export_table` (see :ref:`plugin-apis`).
