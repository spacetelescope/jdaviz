
.. _quickstart:

Quickstart
==========

Once installed, ``jdaviz`` can be run either as a standalone web application or in a Jupyter notebook.

As a Web Application
------------------------

``jdaviz`` provides a command-line tool to start the web application. To see the syntax and usage,
from a terminal, type::

    jdaviz --help

The general syntax to start the application is to provide a local filename path and an application configuration
to load, i.e.::

    jdaviz /path/to/data/file --layout=<configuration>

For example, to load a SDSS MaNGA IFU data cube into ``CubeViz``, you would run the following from a terminal::

    jdaviz /my/manga/cube/manga-8485-1901-LOGCUBE.fits.gz --layout=cubeviz

In a Jupyter Notebook
---------------------

``jdaviz`` provides a directory of sample notebooks to test the application, located in the `notebooks` sub-directory
of the git repository.  `Example.ipynb` is provided as an example that loads a SDSS MaNGA IFU data cube with the
``CubeViz`` configuration.  To run the provided example, start the jupyter kernel with the notebook path::

    jupyter notebook /path/to/jdaviz/notebooks/Example.ipynb

or simply start a new Jupyter notebook and run the following in a cell::

    from jdaviz import Application

    app = Application()
    app

To learn more about the various ``jdaviz`` application configurations and loading data, see the :ref:`cubeviz`,
:ref:`specviz`, or :ref:`mosviz` tools.
