.. _mosviz-import-data:

***********
Import Data
***********

Mosviz provides two different ways to load data: Auto-recognition directory loading
or manual loading:

Automatic Directory Loading
---------------------------
Mosviz provides instrument-specific directory parsers for select instruments. At this
time, Mosviz supports automatic parsing for the following instruments:

* JWST NIRSpec
* JWST NIRISS

In a Jupyter context (notebook or lab), you can specify the instrument with a directory
as such:

    >>> from jdaviz import Mosviz
    >>> mosviz = Mosviz()
    >>> mosviz.load_data(directory="path/to/my/data", instrument="nirspec")

or for NIRISS:

    >>> mosviz.load_data(directory="path/to/my/data", instrument="niriss")

If an instrument isn't specified, Mosviz will default to NIRSpec parsing.

Specifying an instrument from the command line isn't supported yet, and will default to
NIRSpec parsing as if an instrument wasn't provided:

    jdaviz /path/to/my/data --layout=mosviz

Manual Loading
--------------

If an automatic parser isn't provided yet for your data, Mosviz provides manual loading by
specifying which files are which, and the associations between them. This is done by
generating three lists containing the filenames for the 1D spectra, 
2D spectra, and images in your dataset. These three lists are taken as arguments 
by :meth:`~jdaviz.configs.mosviz.helper.Mosviz.load_data`. The association between files is
assumed to be the order of each list. (e.g. The first object consists of the first filenames
specified in each list, the second target is the second in each list, and so forth.)

Currently, manual loading is supported in the Jupyter context only.

An example is given below, where ``file_dir`` is a
directory that contains all the files for the dataset to be loaded::

    >>> from jdaviz import Mosviz
    >>> mosviz = Mosviz()
    >>> spectra_1d = ['target1_1d.fits', 'target2_1d.fits']
    >>> spectra_2d = ['target1_2d.fits', 'target2_2d.fits']
    >>> images = ['target1_img.fits', 'target2_img.fits']
    >>> mosviz.load_data(spectra_1d, spectra_2d, images)  # doctest: +SKIP
