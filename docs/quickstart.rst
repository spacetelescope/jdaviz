
.. _quickstart:

Quickstart
==========

Once installed, ``jdaviz`` can be run either as a standalone web application in your browser, or
more powerfully, integrated into your Jupyter notebook workflow. Detailed workflows are given
within the documentation, but some quick-start tips are given below.

To see the syntax and usage, from a terminal, call Jdaviz with the ``--help`` flag::

    jdaviz --help

Launcher
--------

For a guided introduction to ``jdaviz``, the included launcher can be invoked either from the command-line::

    jdaviz

or from within a Jupyter notebook workflow::

    import jdaviz
    jdaviz.open()

.. image:: ./img/launcher.png
    :alt: Jdaviz Launcher

By default, the file-path field is left empty. By selecting an availble configuration below, the tool will
start with in a blank state (with no data loaded). The IMPORT button will be available to select a file
from a proper file picker.

Config Auto-Identification
^^^^^^^^^^^^^^^^^^^^^^^^^^

Providing a valid filepath to the launcher will attempt to automatically identify a compatible confirguation.
To do this, enter a filepath into the filepath field, or invoke the launcher with a filepath.

Command-line::

    jdaviz /path/to/a/data/file.fits

Jupyter Notebook::

    import jdaviz
    jdaviz.open("/path/to/a/data/file.fits")

Creating a configuration
------------------------

You can also manually select a specific configuration and not invoke the launcher instead:

In a Jupyter Notebook
^^^^^^^^^^^^^^^^^^^^^

Within any Jupyter Notebook::

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
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Typical usage to load a file into a desired configuration::

    jdaviz --layout=[imviz|specviz|cubeviz|mosviz] /path/to/data/file

For example, to load a FITS image into Imviz::

    jdaviz --layout=imviz my_image.fits

To learn more about the various ``jdaviz`` application configurations and loading data,
see the :ref:`imviz`, :ref:`specviz`, :ref:`cubeviz`, or :ref:`mosviz` tools.
