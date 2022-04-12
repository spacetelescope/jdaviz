
.. _quickstart:

Quickstart
==========

Once installed, ``jdaviz`` can be run either as a standalone web application or in a Jupyter notebook.

As a Web Application
--------------------

``jdaviz`` provides a command-line tool to start the web application. To see the syntax and usage,
from a terminal, type::

    jdaviz --help
    jdaviz /path/to/data/spectral_file --layout=specviz

For example, to load a `SDSS MaNGA IFU data cube <https://data.sdss.org/sas/dr14/manga/spectro/redux/v2_1_2/8485/stack/manga-8485-1901-LOGCUBE.fits.gz>`_ into ``Cubeviz``, you would run the following from a terminal::

    jdaviz /my/manga/cube/manga-8485-1901-LOGCUBE.fits.gz --layout=cubeviz

In a Jupyter Notebook
---------------------

The power of ``jdaviz`` is that it can integrated into your Jupyter notebook workflow::

    from jdaviz import Specviz

    app = Specviz()
    app
To learn more about the various ``jdaviz`` application configurations and loading data, see the
`specviz <https://jdaviz.readthedocs.io/en/latest/specviz/import_data.html>`_, `cubeviz <https://jdaviz.readthedocs.io/en/latest/cubeviz/import_data.html>`_, `mosviz <https://jdaviz.readthedocs.io/en/latest/mosviz/import_data.html>`_, or `imviz <https://jdaviz.readthedocs.io/en/latest/imviz/import_data.html>`_ tools.

``jdaviz`` also provides a directory of `sample notebooks <https://jdaviz.readthedocs.io/en/latest/sample_notebooks.html>`_ to test the application, located in the ``notebooks`` sub-directory
of the git repository.  ``Example.ipynb`` is provided as an example that loads a SDSS MaNGA IFU data cube with the
``Cubeviz`` configuration.  To run the provided example, start the jupyter kernel with the notebook path::

    jupyter notebook /path/to/jdaviz/notebooks/Example.ipynb

To learn more about the various ``jdaviz`` application configurations and loading data, see the :ref:`cubeviz`,
:ref:`specviz`, :ref:`mosviz`, or :ref:`imviz` tools.
