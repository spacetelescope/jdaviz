.. _export_data:

***********************************
Export Data From Jdaviz to Notebook
***********************************

Specific instructions on exporting data from Jdaviz to your notebook vary slightly for each instance of Jdaviz, including for :ref:`Specviz <specviz-notebook>`, :ref:`Cubeviz <cubeviz-notebook>`, :ref:`Mosviz <mosviz-notebook>`, and :ref:`Imviz <imviz-notebook>`.  In all instances, however, you can export data products from the Jdaviz into your notebook and, ultimately, save those variables locally.

Export Position Regions (Imviz)
-------------------------------

In `~jdaviz.configs.imviz.helper.Imviz`, you can extract positional regions::

    regions = myviz.get_interactive_regions()
    regions

Export Spectra
--------------

To export spectra currently loaded into the instance of your app back into your notebook do::

    spectra = myviz.get_spectra()

which yields a `specutils.Spectrum1D` object that you can manipulate however
you wish.  You can then load the modified spectrum back into the notebook via
the API described in :ref:`api-import`.

Alternatively, if you want more control over Specviz, you can access it the
via the lower-level application interface that connects to the ``glue-jupyter``
application level.  This is accessed via the ``.app`` attribute of the
`~jdaviz.configs.specviz.helper.Specviz` helper class.  For more on what you can do with this lower-level object, see the API sections
and the
`glue-jupyter documentation <https://glue-jupyter.readthedocs.io/en/latest/>`_

For a list of available subsets to extract, you can type::

    spectra = myviz.app.get_data_from_viewer('spectrum-viewer')
    spectra

To extract data from you spectrum-viewer::

    spectrum = myviz.app.get_data_from_viewer('spectrum-viewer','Subset 1')

Export Spectral Regions
-----------------------

If you have spectral region subsets, you can extract the parameters of these subsets as an Astropy `spectral region <https://specutils.readthedocs.io/en/stable/spectral_regions.html>`_.  For a list of available spectral regions to extract, you can type::

    regions = myviz.specviz.get_spectral_regions()
    regions

To extract the spectral region you want::

    myregion = regions["Subset 2"]

Export Data from Image Viewer
-----------------------------

In Cubeviz, three image viewers display your data:

 |   Top Left: ``flux-viewer``
 |   Center: ``uncert-viewer``
 |   Top Right: ``mask-viewer``

If you have modified your data cube and have new data in one of your image viewers, you can extract it.  To list the data available in a particular viewer::

    data = myviz.app.get_data_from_viewer("uncert-viewer")
    data

To extract the data you want::

    mydata = myviz.app.get_data_from_viewer("uncert-viewer", "contents")

The data is returned as a ``glue-jupyter`` object.  To convert to a numpy array::

    mydata_flux = mydata["flux"]

Alternatively, you can wrap this all into a single command::

    mydata = myviz.app.get_data_from_viewer("uncert-viewer", "contents[FLUX]")

Export Model and Model Parameters
---------------------------------

After fitting a :ref:`specviz-plugins`, you can extract the `Astropy model <https://docs.astropy.org/en/stable/modeling/index.html>`_ and/or model parameters.  For a list of models::

    models = myviz.get_models()
    models


To extract a specific model::

    mymodel = myviz.get_model_parameters(model_label="ModelLabel", x=x, y=y)

where the model_label parameter identifies which model should be returned and the x and y parameters identify specifically which spaxel fits are to be returned, for models applied to every spaxel using the Apply to Cube button. Leaving x or y as None will mean that the models fit to every spaxel across that axis will be returned.

To extract the model parameters::

    myparams = myviz.get_model_parameters(model_label="ModelLabel", x=x, y=y)

You can then access the model parameter values::

    myparams['ModelLabel']['parameter']

