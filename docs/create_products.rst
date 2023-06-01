.. _create_products:

Create Jdaviz-readable Products
===============================

Spectroscopic data products (1D, 2D, and 3D) can be loaded in the different Jdaviz configurations using
essentially two methods, i.e. loading :class:`~specutils.Spectrum1D` objects, or loading
from FITS files. Here, we list a few ways in which data can be packaged to be easily loaded
into a ``jdaviz`` configuration.

Data in a database
------------------

If the data are stored in a database, we recommend storing a :class:`~specutils.Spectrum1D` object
per entry. This would allow the user to query the data and visualize it in
``jdaviz`` with few lines of code.

Data in FITS files
------------------

If the data are stored as FITS files, we propose three options: the user can
adopt any of the formats readable by specutils; or they can create their own
specialized loader; or they can provide scripts to read the FITS products as
:class:`~specutils.Spectrum1D` objects.

Using an available specutils loader
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Available loaders can be listed with the following commands:

.. code-block:: python

    from specutils import Spectrum1D
    Spectrum1D.read.list_formats()

The majority are fairly specific to missions and instruments. Four formats
are more generic and adaptable: ``ASCII``, ``ECSV``, ``tabular-fits``, and
``wcs1d-fits``. More information on how to create files that are readable by
these loaders can be found on the `specutils github repository
<https://github.com/astropy/specutils/tree/main/specutils/io/default_loaders>`_.

Creating a dedicated loader
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The `specutils documentation on how to create a custom loader
<https://specutils.readthedocs.io/en/stable/custom_loading.html#creating-a-custom-loader>`_
is available. We are working on the necessary documentation to prompt
``jdaviz`` to recognize a custom loader developed in ``specutils``.

Providing scripts to load the data as Spectrum1D objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If none of the above is an acceptable option, the user can create the data
products with their custom format and provide scripts or Jupyter Notebooks
that show how to read the products and create :class:`~specutils.Spectrum1D` objects
that can be read into ``jdaviz``. More about
how to create :class:`~specutils.Spectrum1D` objects for the 1D, 2D, and 3D cases can be
found in the corresponding "Importing data" sections of the various configurations.
