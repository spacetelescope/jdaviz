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

    subset1_spec1d = cubeviz.specviz.get_spectra(spectral_subset="Subset 1")

An example without accessing Specviz:

.. code-block:: python

    subset1_spec1d = cubeviz.get_data(data_label=flux_data_label, 
                                      spatial_subset="Subset 1",
                                      function="mean")

Note that in the above example, the ``function`` keyword is used to tell Cubeviz
how to collapse the flux cube down to a one dimensional spectrum - this is not 
necessarily equivalent to the collapsed spectrum in the spectrum viewer, which 
may have used a different collapse function.

To get all subsets from the spectrum viewer:

.. code-block:: python

    subset1_spec1d = cubeviz.specviz.app.get_subsets()

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

3D Data Cubes
=============

To extract the entire cube, you can run the following code (replace "data_name"
with the name of the data you want to extract):

.. code-block:: python

    mydata = cubeviz.get_data(data_label="data_name")

The data is returned as a 3D `specutils.Spectrum1D` object.

To write out a `specutils.Spectrum1D` cube from Cubeviz
(e.g., a fitted cube from :ref:`model-fitting`),
where the mask (if available) is as defined in
`Spectrum1D masks <https://specutils.readthedocs.io/en/latest/spectrum1d.html#including-masks>`_:

.. code-block:: python

    mydata.write("mydata.fits", format="jdaviz-cube")

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

Markers Table
=============

All mouseover information in the :ref:`markers plugin <markers-plugin>` can be exported to an
:ref:`astropy table <astropy:astropy-table>`
by calling :meth:`~jdaviz.core.template_mixin.TableMixin.export_table` (see :ref:`plugin-apis`).
