.. _specviz-export-data:

***************************
Exporting Data From Specviz
***************************

1D Spectra
==========

After data have been manipulated or analyzed, it is possible to export
those data currently back into your Jupyter notebook::

    specviz.get_spectra()

which yields a `specutils.Spectrum1D` object that you can manipulate however
you wish.  You can then load the modified spectrum back into the notebook via
the API described in :ref:`specviz-import-api`.

Alternatively, if you want more control over Specviz, you can access it the
via the lower-level application interface that connects to the ``glue-jupyter``
application level.  This is accessed via the ``.app`` attribute of the
`~jdaviz.configs.specviz.helper.Specviz` helper class.  For example::

    specviz.app.get_data_from_viewer('spectrum-viewer')

To extract a specific spectral subset::

    specviz.app.get_data_from_viewer('spectrum-viewer', 'Subset 1')

For more on what you can do with this lower-level object, see the API sections
and the
`glue-jupyter documentation <https://glue-jupyter.readthedocs.io/en/latest/>`_.

.. seealso::

    :ref:`Export From Plugins <specviz-plugins>`
        Calculations (i.e., not spectroscopic data) from the plugins can also be exported back into the Jupyter notebook in some cases.

Spectral Regions
================

If you have spectral region subsets, you can extract the parameters of these subsets
as a `specutils spectral region <https://specutils.readthedocs.io/en/stable/spectral_regions.html>`_.
For a list of available spectral regions to extract, you can type::

    regions = specviz.get_spectral_regions()
    regions

To extract the spectral region you want::

    myregion = regions["Subset 2"]

.. _specviz-export-model:

Model Fits
==========

For a list of model labels::

    models = cubeviz.get_models()
    models

Once you know the model labels, to get a specific model::

    mymodel = cubeviz.get_models(model_label="ModelLabel", x=10)

To extract all of the model parameters::

    myparams = cubeviz.get_model_parameters(model_label="ModelLabel", x=x, y=y)
    myparams

where the model_label parameter identifies which model should be returned and
the x and y parameters identify specifically which spaxel fits are to be returned,
for models applied to every spaxel using the Apply to Cube button.
Leaving x or y as None will mean that the models fit to every spaxel across that axis will be returned.
