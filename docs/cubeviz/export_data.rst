.. _cubeviz-notebook:

***************************
Exporting Data from Cubeviz
***************************

After data have been manipulated or analyzed, it is possible to export
those data currently back into your Jupyter notebook.

.. _cubeviz_export_regions:

Spatial Regions
===============

.. seealso::

    :ref:`Export Spatial Regions <imviz_export>`
        Documentation on how to export spatial regions.

Since Specviz can be accessed from Cubeviz, the following line of code
can be used to extract the *spectrum* of a spatial subset named "Subset 1":

.. code-block:: python

    subset1_spec1d = cubeviz.specviz.get_spectra("Subset 1")

An example without accessing Specviz:

.. code-block:: python

    subset1_spec1d = cubeviz.app.get_data_from_viewer("flux-viewer", data_label="Subset 1")

To get all subsets from the spectrum viewer:

.. code-block:: python

    subset1_spec1d = cubeviz.app.get_subsets_from_viewer("spectrum-viewer")

To access the spatial regions themselves:

.. code-block:: python

    regions = cubeviz.get_interactive_regions()
    regions

1D Spectra and Spectral Regions
===============================

.. seealso::

    :ref:`Export Spectra <specviz-export-data>`
        Documentation on how to export data from the ``spectrum-viewer``.

The following line of code can be used to extract a spectral subset named "Subset 2":

.. code-block:: python

    subset2_spec1d = cubeviz.specviz.get_spectra("Subset 2")

2D Images and 3D Data Cubes
===========================

2D images and 3D data cubes can be extracted from their respective
:ref:`viewers <cubeviz-viewers>`. The viewer options in the Cubeviz configuration are
``flux-viewer``, ``uncert-viewer``, and ``mask-viewer``.
For example, to list the data available in a particular viewer:

.. code-block:: python

    mydata = cubeviz.app.get_data_from_viewer("flux-viewer")

To extract the data you want (replace "data_name" with the name of your data):

.. code-block:: python

    mydata = cubeviz.app.get_data_from_viewer("uncert-viewer", "data_name")

The data is returned as a ``glue-jupyter`` object.  To convert to a numpy array:

.. code-block:: python

    mydata_flux = mydata["flux"]

To retrieve the data cube as a `specutils.Spectrum1D` object, you can do the following:

.. code-block:: python

    from specutils import Spectrum1D
    mydata.get_object(cls=Spectrum1D, statistic=None)

Alternatively, you can wrap this all into a single command:

.. code-block:: python

    mydata = cubeviz.app.get_data_from_viewer("uncert-viewer", "data_name")

To write out a `specutils.Spectrum1D` cube from Cubeviz
(e.g., a fitted cube from :ref:`model-fitting`):

.. code-block:: python

    mydata.write("mydata.fits", format="jdaviz-cube-writer")

Data can also be accessed directly from ``data_collection`` using the following code:

.. code-block:: python

    cubeviz.app.data_collection[0]

Which is returned as a `~glue.core.data.Data` object. The
`~glue.core.data_collection.DataCollection` object
can be indexed to return all available data (i.e., not just using 0 like in the
previous example).

.. _cubeviz-export-model:

Model Fits
==========

For a list of model labels:

.. code-block:: python

    models = cubeviz.get_models()
    models

Once you know the model labels, to get a specific model:

.. code-block:: python

    mymodel = cubeviz.get_models(model_label="ModelLabel", x=10)

To extract all of the model parameters:

.. code-block:: python

    myparams = cubeviz.get_model_parameters(model_label="ModelLabel", x=x, y=y)
    myparams

where the ``model_label`` parameter identifies which model should be returned and
the ``x`` and ``y`` parameters identify specifically which spaxel fits are to be returned,
for models applied to every spaxel using the :guilabel:`Apply to Cube` button.
Leaving ``x`` or ``y`` as ``None`` will mean that the models fit to every spaxel
across that axis will be returned.
