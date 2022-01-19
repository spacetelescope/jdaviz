
.. _quickstart:

Quickstart
==========

Once installed, ``jdaviz`` can be run either as a standalone web application or in a Jupyter notebook.

As a Web Application
--------------------

``jdaviz`` provides a command-line tool to start the web application. To see the syntax and usage,
from a terminal, type::

    jdaviz --help

The general syntax to start the application is to provide a local filename path and an application configuration
to load, i.e.::

    jdaviz /path/to/data/file --layout=<configuration>

For example, to load a `SDSS MaNGA IFU data cube <https://data.sdss.org/sas/dr14/manga/spectro/redux/v2_1_2/8485/stack/manga-8485-1901-LOGCUBE.fits.gz>`_ into ``Cubeviz``, you would run the following from a terminal::

    jdaviz /my/manga/cube/manga-8485-1901-LOGCUBE.fits.gz --layout=cubeviz

In a Jupyter Notebook
---------------------

``jdaviz`` provides a directory of sample notebooks to test the application, located in the ``notebooks`` sub-directory
of the Git repository.  For instance, the following example loads a SDSS MaNGA IFU data cube with the
Cubeviz configuration.  To run it, start the Jupyter kernel with the notebook path::

    jupyter notebook /path/to/jdaviz/notebooks/CubevizExample.ipynb

To learn more about the various ``jdaviz`` application configurations and loading data, see
:ref:`notebook_import_data`, :ref:`cubeviz`, :ref:`specviz`, :ref:`mosviz`, or :ref:`imviz`.
