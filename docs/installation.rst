
.. _install:

Installation
============

The following details how to install the ``jdaviz`` Python package.

If you encounter problems while following these installation instructions,
please consult :ref:`known installation issues <known_issues_installation>`.

You may want to consider installing ``jdaviz`` in a new virtual or conda environment
to avoid version conflicts with other packages you may have installed.

Quick Installation
------------------

Installing the released version can be done using pip::

   pip install jdaviz --upgrade

or if you want the latest development version, you can install via GitHub::

   pip install git+https://github.com/spacetelescope/jdaviz --upgrade

Note that ``jdaviz`` requires Python 3.8 or newer.  If your pip corresponds to an older version of 
Python, it will state an error that it cannot find a valid package.

Developer Installation
----------------------

To install ``jdaviz`` for development or from source in editable mode::

   git clone https://github.com/spacetelescope/jdaviz.git
   cd jdaviz
   pip install -e .

To enable the hot reloading of vue templates, install watchdog::

   pip install watchdog

And to the top of a notebook add::

   from jdaviz import enable_hot_reloading
   enable_hot_reloading()

See :ref:`quickstart` to learn how to run ``jdaviz``.
