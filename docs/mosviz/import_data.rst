.. _mosviz-import-api:

**************************
Importing Data into Mosviz
**************************

Mosviz provides two different ways to load data:

* :ref:`mosviz-import-auto-dir`
* :ref:`mosviz-import-manual-loading`

.. _mosviz-import-auto-dir:

Automatic Directory Loading
===========================

Mosviz provides instrument-specific directory parsers for select instruments. At this
time, Mosviz supports automatic parsing for the following instruments:

* :ref:`mosviz-import-auto-dir-nirspec`
* :ref:`mosviz-import-auto-dir-niriss`
* :ref:`mosviz-import-auto-dir-nircam`

In a Jupyter context (notebook or Lab), you must specify the instrument with a directory
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

    jdaviz --layout=mosviz /path/to/my/data --instrument=nirspec

and for NIRISS:

.. code-block:: bash

    jdaviz --layout=mosviz /path/to/my/data --instrument=niriss

Specifying a data directory and an instrument are required to start Mosviz from the command line.
If a directory is entered without specifying an instrument, Mosviz will
raise an error.

.. _mosviz-import-auto-dir-nirspec:

JWST NIRSpec (levels 2 and 3)
-----------------------------

The NIRSpec parser expects a directory with either level 2 files:

* ``*_i2d.fits`` : Cutout images (see below).
* ``*_s2d.fits`` : Single file containing level 2 2D spectra for all objects.
* ``*_x1d.fits`` : Single file containing level 2 1D spectra for all objects.

or level 3 files:

* ``*_s2d.fits`` : N files containing level 3 2D spectra, where N is the number of objects.
* ``*_x1d.fits`` : N files containing level 3 1D spectra, where N is the number of objects.

In either the level 2 or 3 case, the NIRSpec data directory may contain a sub-directory
named ``images``, ``cutouts``, or ``mosviz_cutouts``. This sub-directory should contain FITS files
containing images corresponding to each target, which may be sourced from a non-JWST telescope.
If it only contains a single image, the same image would be used for all the spectra.

.. _mosviz-import-auto-dir-niriss:

JWST NIRISS
-----------

The NIRISS parser expects a directory with the following types of files:

* ``*_i2d.fits`` : Level 3 2D images from the ``calwebb_image3`` imaging pipeline
* ``*_cat.ecsv`` : Level 3 source catalog from the ``calwebb_image3`` imaging pipeline **(For best performance, it's recommended that your directory only contain one.)**
* ``*_cal.fits`` : Level 2 2D spectra in vertical (R) and horizontal (C) orientations from the ``calwebb_spec2`` spectroscopic pipeline *(C spectra are shown first in 2D viewer by default.)*
* ``*_x1d.fits`` : Level 2 1D spectra in vertical (R) and horizontal (C) orientations from the ``calwebb_spec2`` spectroscopic pipeline *(C spectra are shown first in 1D viewer by default.)*

.. _mosviz-import-auto-dir-nircam:

JWST NIRCam
-----------

The NIRCam parser expects ``*_cal.fits`` and ``*_x1d`` files in the same format as the NIRISS parser.

.. _mosviz-import-manual-loading:

Manual Loading
==============

If an automatic parser is not provided yet for your data, Mosviz provides manual loading by
specifying which files are which, and the associations between them. This is done by
generating three lists containing the filenames for the 1D spectra,
2D spectra, and images in your dataset (if you are creating your own data products,
please read the page :ref:`create_products`). 
These three lists are taken as arguments
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
    mosviz.load_data(spectra_1d=spectra_1d, spectra_2d=spectra_2d, images=images)
    mosviz.show()

Alternatively, if you want all the spectra to share a single image (e.g., a mosaic):

.. code-block:: python

    from jdaviz import Mosviz
    mosviz = Mosviz()
    spectra_1d = ['target1_1d.fits', 'target2_1d.fits']
    spectra_2d = ['target1_2d.fits', 'target2_2d.fits']
    image = 'mymosaic.fits'
    mosviz.load_data(spectra_1d=spectra_1d, spectra_2d=spectra_2d, images=image)
    mosviz.show()
