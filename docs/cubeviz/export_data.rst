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

Any cube (or extracted spectrum) can be extracted from cubeviz:

.. code-block:: python

    subset1_spec1d = cubeviz.get_data("Spectrum (Subset 1, sum)")


To use a ``function`` other than sum, use the :ref:`Spectral Extraction <spectral-extraction>` plugin
first to create a 1D spectrum and then refer to it by label in ``get_data``.

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

The following line of code can be used to extract 1D spectrum either automatically extracted
or extracted manually through the :ref:`Spectral Extraction <spectral-extraction>` plugin:

.. code-block:: python

    subset2_spec1d = cubeviz.get_data("Spectrum (Subset 2, sum)")

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

    mydata.write("mydata.fits", format="wcs1d-fits", hdu=1)


.. _cubeviz-export-model:

Model Fits
==========

For a list of model labels:

.. code-block:: python

    models = cubeviz.plugins['Model Fitting'].get_models()
    models

Once you know the model labels, to get a specific model:

.. code-block:: python

    mymodel = cubeviz.plugins['Model Fitting'].get_models(model_label="ModelLabel", x=10)

To extract all of the model parameters:

.. code-block:: python

    myparams = cubeviz.plugins['Model Fitting'].get_model_parameters(model_label="ModelLabel", x=x, y=y)
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


.. _cubeviz_export_photometry:

Aperture Photometry
===================

Cubeviz can export photometry output table like Imviz:

.. code-block:: python

    results = cubeviz.get_aperture_photometry_results()

.. seealso::

    :ref:`Imviz Aperture Photometry <imviz_export_photometry>`
        Imviz documentation describing exporting of aperture photometry results in Jdaviz.

In addition to the columns that :ref:`Imviz Aperture Photometry <imviz_export_photometry>`
would provide, the table from Cubeviz has this extra column after ``data_label``:

* ``slice_wave``: Wavelength value at the selected slice of the cube used for computation.
  If a 2D data (e.g., collapsed cube) is selected, the value would be NaN instead.
