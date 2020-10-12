.. _mosviz-import-data:

***********
Import Data
***********

Currently, data must be imported into Mosviz using the API in the Jupyter notebook. 
After initializing the app as explained in :ref:`mosviz-notebook`, 
you must generate three lists containing the filenames for the 1D spectra, 
2D spectra, and images in your dataset. These three lists are taken as arguments 
to the Mosviz `load_data` method. An example is given below, where `file_dir` is a 
directory that contains all the files for the dataset to be loaded::

    >>> from jdaviz import MosViz
    >>> mosviz = MosViz()
    >>> mosviz.app #doctest: +SKIP
    >>> spectra_1d = []
    >>> spectra_2d = []
    >>> images = []
    >>> for filename in glob("{}/*".format(file_dir)): #doctest: +SKIP
    >>>     if "x1d" in filename: #doctest: +SKIP
    >>>         spectra_1d.append(filename) #doctest: +SKIP
    >>>     elif "s2d" in filename: #doctest: +SKIP
    >>>         spectra_2d.append(filename) #doctest: +SKIP
    >>>     elif "fits" in filename: #doctest: +SKIP
    >>>         images.append(filename) #doctest: +SKIP
    >>>     mosviz.load_data(spectra_1d, spectra_2d, images) #doctest: +SKIP

This example assumes that all 1D spectra have "x1d" in the filename, all 2D spectra
have "s2d" in the filename, and any other FITS files in the directory are the 
corresponding images. 
