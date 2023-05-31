.. _create_products:

Create Jdaviz-readable Products
===============================

Data products can be loaded in the different Jdaviz configurations using
various methods, e.g. loading :class:`~specutils.Spectrum1D` objects, loading
from fits files, or loading a set of fits files from a directory.
Here, we list a few ways in which data can be packaged to be easily loaded
into a ``jdaviz`` configuration.

Data in a database
------------------

If the data are stored in a database, we recommend storing a :class:`~specutils.Spectrum1D` object
per entry. This would allow the user to query the data and visualize it in
Jdaviz with few lines of code. This is an example with an imaginary database.

.. code-block:: python

    from database import Client
    from jdaviz import Specviz

    client = Client()
    search = client.find(**options**)
    results = client.retrieve(search)
    spec1d = results[0]['Spectrum1D']

    specviz = Specviz()
    specviz.load_data(spec1d, data_label='my spectrum')
    specviz.show()


Data in fits files
------------------

If the data are stored as fits files, we propose three options: user can
adopt any of the formats readable by specutils; user can create their own
specialized loader; user can provide scripts to read the fits products as
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
is available. We are working on the necessary documentation to allow
``jdaviz`` to recognize a custom loader developed in ``specutils``.

Providing scripts to load the data as Spectrum1D objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If none of the above is an acceptable option, the user can create the data
products with their custom format and provide scripts or Jupyter Notebooks
that show how to read the products and create :class:`~specutils.Spectrum1D` objects (or
arrays in the case of ``Imviz``) that can be read into ``jdaviz``. More about
how to create Spectrum1D or arrays can be
found in the corresponding "Importing data" sections of the various configurations.
