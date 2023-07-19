
.. _quickstart:

Quickstart
==========

Once installed, ``jdaviz`` can be run either in a Jupyter notebook or as a standalone web application.
Detailed workflows are given within the documentation, but some quick-start tips are given below.

In a Jupyter Notebook
---------------------

The power of Jdaviz is that it can integrated into your Jupyter notebook workflow::

    from jdaviz import Imviz

    imviz = Imviz()
    imviz.show()
    imviz.load_data('filename.fits', data_label='MyData')

Jdaviz also provides a directory of :ref:`sample notebooks <sample_notebook>`
to test the application, located in the :gh-tree:`notebooks` sub-directory of the Git repository.
:gh-notebook:`ImvizExample.ipynb <ImvizExample>` is provided as an example that loads
two 47 Tucanae exposures taken with HST/ACS WFC detectors with the ``Imviz`` configuration.
To run the provided example, start the Jupyter kernel with the notebook path::

    jupyter notebook /path/to/jdaviz/notebooks/ImvizExample.ipynb

Alternately, if you are using Jupyter Lab::

    jupyter lab /path/to/jdaviz/notebooks/ImvizExample.ipynb

As a Standalone Application
---------------------------

``jdaviz`` provides a command-line tool to start the standalone desktop application in a browser. 
To see the syntax and usage, from a terminal, type::

    jdaviz --help

Typical usage to load a file into a desired configuration::

    jdaviz [imviz|specviz|cubeviz|mosviz] /path/to/data/file

For example, to load a FITS image into Imviz::

    jdaviz imviz my_image.fits

To learn more about the various ``jdaviz`` application configurations and loading data,
see the :ref:`imviz`, :ref:`specviz`, :ref:`cubeviz`, or :ref:`mosviz` tools.
