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

which yields a `specutils.Spectrum1D` object that you can manipulate however
you wish.  You can then load the modified spectrum back into the notebook via
the API described in :ref:`specviz-import-api`.

Alternatively, if you want more control over Specviz, you can access it the
via the lower-level application interface that connects to the ``glue-jupyter``
application level.  This is accessed via the ``.app`` attribute of the
:py:class:`~jdaviz.configs.specviz.helper.Specviz` helper class.  For example:

.. code-block:: python

    specviz.app.get_data_from_viewer('spectrum-viewer')

To extract a specific spectral subset:

.. code-block:: python

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
