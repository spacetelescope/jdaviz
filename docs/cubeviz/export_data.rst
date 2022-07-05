.. _cubeviz-notebook:

***************************
Exporting Data from Cubeviz
***************************

After data have been manipulated or analyzed, it is possible to export
those data currently back into your Jupyter notebook.

Spatial Regions
===============================

.. seealso::

    :ref:`Export Spatial Regions <imviz_export>`
        Documentation on how to export spatial regions.

1D Spectra and Spectral Regions
===============================

.. seealso::

    :ref:`Export Spectra <specviz-export-data>`
        Documentation on how to export data from the ``spectrum-viewer``.

2D and 3D Data Cubes
====================

2D and 3D data cubes can be extracted from their respective :ref:`viewers <cubeviz-viewers>`.
The viewer options in the Cubeviz configuration are ``flux-viewer``, ``uncert-viewer``, and ``mask-viewer``.
For example, to list the data available in a particular viewer:::

    mydata = cubeviz.app.get_data_from_viewer('flux-viewer')

To extract the data you want::

    mydata = cubeviz.app.get_data_from_viewer("uncert-viewer", "contents")

The data is returned as a ``glue-jupyter`` object.  To convert to a numpy array::

    mydata_flux = mydata["flux"]

Alternatively, you can wrap this all into a single command::

    mydata = cubeviz.app.get_data_from_viewer("uncert-viewer", "contents[FLUX]")

Data can also be accessed directly from ``data_collection`` using the following code::

    cubeviz.app.data_collection[0]

Which is returned as a `~glue.core.data.Data` object. The
`~glue.core.data_collection.DataCollection` object
can be indexed to return all available data (i.e., not just using 0 like in the
previous example).

.. _cubeviz-export-model:

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

