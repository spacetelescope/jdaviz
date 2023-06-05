.. _create_products:

Creating Jdaviz-readable Products
=================================

Spectroscopic data products (1D, 2D, and 3D) can be loaded
in the different ``jdaviz`` configurations using
essentially two methods, i.e., loading :class:`~specutils.Spectrum1D` objects or
from FITS files. Here, we list a few ways in which data can be packaged to be easily loaded
into a ``jdaviz`` configuration.

Data in a database
------------------

If the data are stored in a database, we recommend storing a :class:`~specutils.Spectrum1D` object
per entry. This would allow the user to query the data and visualize it in
``jdaviz`` with few lines of code; also see :ref:`create_product_spectrum1d_obj`.

Data in FITS files
------------------

If the data are stored as FITS files, we propose three options:

* :ref:`create_product_specutils_loader`
* :ref:`create_product_dedicated_loader`
* :ref:`create_product_spectrum1d_obj`

.. _create_product_specutils_loader:

Using an available specutils loader
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Available loaders can be listed with the following commands:

.. code-block:: python

    from specutils import Spectrum1D
    Spectrum1D.read.list_formats()

The majority are fairly specific to missions and instruments. Four formats
are more generic and adaptable: ``ASCII``, ``ECSV``, ``tabular-fits``, and
``wcs1d-fits``. More information on how to create files that are readable by
these loaders can be found on the `specutils GitHub repository
<https://github.com/astropy/specutils/tree/main/specutils/io/default_loaders>`_.

.. _create_product_dedicated_loader:

Creating a dedicated loader
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The `specutils documentation on how to create a custom loader
<https://specutils.readthedocs.io/en/stable/custom_loading.html#creating-a-custom-loader>`_
is available. We are working on the necessary documentation to prompt
``jdaviz`` to recognize a custom loader developed in ``specutils``.

.. _create_product_spectrum1d_obj:

Providing scripts to load the data as Spectrum1D objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If none of the above is an acceptable option, the user can create the data
products with their custom format and provide scripts or Jupyter Notebooks
that show how to read the products and create :class:`~specutils.Spectrum1D` objects
that can be read into ``jdaviz``. More about
how to create :class:`~specutils.Spectrum1D` objects for the 1D, 2D, and 3D cases can be
found in the corresponding "Importing data" sections of the various configurations:

* :ref:`specviz-import-data`
* :ref:`cubeviz-import-data`
* :ref:`specviz2d-import-data`
* :ref:`mosviz-import-api`
