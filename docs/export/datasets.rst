.. _export-datasets:
.. rst-class:: section-icon-mdi-content-save

********
Datasets
********

Documentation coming soon. See :ref:`export` for general export information.

UI Access
=========

.. wireframe-demo::
   :demo: save
   :enable-only: save
   :demo-repeat: false


Top-Level API Access
====================


The :attr:`~jdaviz.core.helpers.ConfigHelper.datasets` property provides API access to all data loaded in Jdaviz.
This property returns a dictionary of data API objects that allow you to retrieve data, export to python objects in the notebook,
and manipulate within the app.

.. code-block:: python

    import jdaviz as jd

    jd.show()
    jd.load('mydata.fits', format='1D Spectrum', data_label='spectrum')

    # Access all datasets
    datasets = jd.datasets
    # Returns: {'spectrum': <Data API for spectrum>}

    # Access a specific dataset
    spectrum_api = jd.datasets['spectrum']

Each dataset is wrapped in a specialized data API object depending on the data type:

- :class:`~jdaviz.core.user_api.SpectralDataApi`: For 1D and 2D spectra (Specviz, Specviz2D)
- :class:`~jdaviz.core.user_api.SpatialDataApi`: For 2D images (Imviz)
- :class:`~jdaviz.core.user_api.SpectralSpatialDataApi`: For 3D cubes (Cubeviz, Mosviz)
- :class:`~jdaviz.core.user_api.TemporalSpatialDataApi`: For ramp data (Rampviz)
- :class:`~jdaviz.core.user_api.DataApi`: Base class, used as fallback

All data API objects provide common methods for working with your data.

- :meth:`~jdaviz.core.user_api.DataApi.get_data`
- :meth:`~jdaviz.core.user_api.DataApi.add_to_viewer`


**Basic usage:**

.. code-block:: python

    # Get the data object
    spectrum = jd.datasets['spectrum'].get_data()

    # Work with the returned object
    print(spectrum.spectral_axis)
    print(spectrum.flux)


Add a dataset to a specific viewer programmatically:

.. code-block:: python

    # Add data to a viewer
    jd.datasets['spectrum'].add_to_viewer('spectrum-viewer')
