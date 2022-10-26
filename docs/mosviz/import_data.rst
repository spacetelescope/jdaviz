.. _mosviz-import-api:

**************************
Importing Data into Mosviz
**************************

Mosviz provides two different ways to load data: auto-recognition directory
loading and manual loading.

Automatic Directory Loading
---------------------------
Mosviz provides instrument-specific directory parsers for select instruments. At this
time, Mosviz supports automatic parsing for the following instruments:

* JWST NIRSpec
* JWST NIRISS

The NIRISS parser expects a directory with the following types of files:

* ``*_i2d.fits`` : Level 3 2D images from the ``calwebb_image3`` imaging pipeline
* ``*_cat.ecsv`` : Level 3 source catalog from the ``calwebb_image3`` imaging pipeline **(For best performance, it's recommended that your directory only contain one.)**
* ``*_cal.fits`` : Level 2 2D spectra in vertical (R) and horizontal (C) orientations from the ``calwebb_spec2`` spectroscopic pipeline *(C spectra are shown first in 2D viewer by default.)*
* ``*_x1d.fits`` : Level 2 1D spectra in vertical (R) and horizontal (C) orientations from the ``calwebb_spec2`` spectroscopic pipeline *(C spectra are shown first in 1D viewer by default.)*

In a Jupyter context (notebook or Lab), you can specify the instrument with a directory
as such:

.. code-block:: python

    from jdaviz import Mosviz
    mosviz = Mosviz()
    mosviz.load_data(directory="path/to/my/data", instrument="nirspec")
    mosviz.show()

or for NIRISS:

.. code-block:: python

    mosviz.load_data(directory="path/to/my/data", instrument="niriss")

Similarly, an instrument keyword can be specified by the command line. For NIRSpec:

.. code-block:: bash

    jdaviz mosviz /path/to/my/data --instrument=nirspec

and for NIRISS:

.. code-block:: bash

    jdaviz mosviz /path/to/my/data --instrument=niriss

If an instrument is not specified in either case, Mosviz will default to NIRSpec parsing.

Manual Loading
--------------

If an automatic parser is not provided yet for your data, Mosviz provides manual loading by
specifying which files are which, and the associations between them. This is done by
generating three lists containing the filenames for the 1D spectra,
2D spectra, and images in your dataset. These three lists are taken as arguments
by :py:meth:`~jdaviz.configs.mosviz.helper.Mosviz.load_data`. The association between files is
assumed to be the order of each list (e.g., the first object consists of the first filename
specified in each list, the second target is the second in each list, and so forth).

Currently, manual loading is supported in the Jupyter context only.

An example is given below, where ``file_dir`` is a
directory that contains all the files for the dataset to be loaded:

.. code-block:: python

    from jdaviz import Mosviz
    mosviz = Mosviz()
    spectra_1d = ['target1_1d.fits', 'target2_1d.fits']
    spectra_2d = ['target1_2d.fits', 'target2_2d.fits']
    images = ['target1_img.fits', 'target2_img.fits']
    mosviz.load_data(spectra_1d, spectra_2d, images)
    mosviz.show()
