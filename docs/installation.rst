
.. _install:

Installation
============

The following details how to install the ``jdaviz`` Python package.

If you encounter problems while following these installation instructions,
please consult :ref:`known installation issues <known_issues_installation>`.

Quick Installation
------------------

Installing the released version can be done using pip::

   pip install jdaviz --upgrade

or if you want the latest development version, you can install via GitHub::

   pip install git+https://github.com/spacetelescope/jdaviz --upgrade

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
