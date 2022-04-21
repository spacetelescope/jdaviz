
.. _quickstart:

Quickstart
==========

Once installed, ``jdaviz`` can be run either as a standalone web application or in a Jupyter notebook.

As a Web Application
--------------------

``jdaviz`` provides a command-line tool to start the web application. To see the syntax and usage,
from a terminal, type::

    jdaviz --help
    jdaviz specviz /path/to/data/spectral_file

For example, to load a `SDSS MaNGA IFU data cube <https://stsci.box.com/shared/static/28a88k1qfipo4yxc4p4d40v4axtlal8y.fits>`_ into ``Cubeviz``, you would run the following from a terminal::

    jdaviz cubeviz /my/manga/cube/manga-7495-12704-LOGCUBE.fits

In a Jupyter Notebook
---------------------

The power of ``jdaviz`` is that it can integrated into your Jupyter notebook workflow::

    from jdaviz import Specviz

    specviz = Specviz()
    specviz.app


``jdaviz`` also provides a directory of :ref:`sample notebooks <sample_notebook>` to test the application, located in the ``notebooks`` sub-directory
of the git repository. ``CubevizExample.ipynb`` is provided as an example that loads a SDSS MaNGA IFU data cube with the
``Cubeviz`` configuration.  To run the provided example, start the jupyter kernel with the notebook path::

    jupyter notebook /path/to/jdaviz/notebooks/CubevizExample.ipynb

To learn more about the various ``jdaviz`` application configurations and loading data, see the :ref:`cubeviz`,
:ref:`specviz`, :ref:`mosviz`, or :ref:`imviz` tools.
