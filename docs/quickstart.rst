
.. _quickstart:

Quickstart
==========

Once installed, ``jdaviz`` can be run either in a Jupyter notebook or as a standalone web application. Detailed workflows are given within the documentation, but some quick start tips are given below.

In a Jupyter Notebook
---------------------

The power of ``jdaviz`` is that it can integrated into your Jupyter notebook workflow::

    from jdaviz import Imviz

    imviz = Imviz()
    imviz.app
    imviz.load_data('filename.fits', data_label='MyData')


``jdaviz`` also provides a directory of :ref:`sample notebooks <sample_notebook>` to test the application,
located in the :gh-tree:`notebooks` sub-directory
of the git repository. :gh-notebook:`CubevizExample.ipynb <CubevizExample>` is provided as an example that loads a SDSS MaNGA IFU data cube with the
``Cubeviz`` configuration.  To run the provided example, start the jupyter kernel with the notebook path::

    jupyter lab /path/to/jdaviz/notebooks/ImvizExample.ipynb

As a Standalone Application
---------------------------

``jdaviz`` provides a command-line tool to start the standalone desktop application in a browser. 
To see the syntax and usage, from a terminal, type::

    jdaviz --help
    jdaviz [cubeviz|specviz|mosviz|imviz] /path/to/data/file

For example, to load a `SDSS MaNGA IFU data cube <https://stsci.box.com/shared/static/28a88k1qfipo4yxc4p4d40v4axtlal8y.fits>`_ into ``Cubeviz``, you would run the following from a terminal::

    jdaviz cubeviz /my/manga/cube/manga-7495-12704-LOGCUBE.fits


To learn more about the various ``jdaviz`` application configurations and loading data, see the :ref:`cubeviz`,
:ref:`specviz`, :ref:`mosviz`, or :ref:`imviz` tools.
