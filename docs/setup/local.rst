
.. _setup-local:

Install Jdaviz for Local Jupyter
=================================

Install Jdaviz in your local Python environment to use it within Jupyter Notebook or Jupyter Lab.

Prerequisites
-------------

* Python 3.9, 3.10, or 3.11
* Jupyter Notebook or JupyterLab
* pip or conda package manager

Windows-Specific Dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Some of our dependencies require C++ compilers to install properly. These are usually
included with macOS and most Linux distributions, but are not included by default in
Windows. Microsoft provides these tools as part of their
`Build Tools for Visual Studio <https://visualstudio.microsoft.com/downloads>`_,
which can be found under "Tools for Visual Studio" towards the bottom of the page.

Create Your Environment
------------------------

We recommend creating a dedicated environment for Jdaviz to avoid package conflicts.

Using Conda (Recommended)
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    conda create -n jdaviz-env python=3.11
    conda activate jdaviz-env

Using venv
^^^^^^^^^^

.. code-block:: bash

    python -m venv jdaviz-env
    source jdaviz-env/bin/activate  # On Windows: jdaviz-env\Scripts\activate

Installation
------------

Latest Development Version (Recommended)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We typically recommend installing the latest development version for access to the
newest features and bug fixes:

.. code-block:: bash

    pip install git+https://github.com/spacetelescope/jdaviz --upgrade

Latest Release Version
^^^^^^^^^^^^^^^^^^^^^^

To install the latest stable release:

.. code-block:: bash

    pip install jdaviz

Install JupyterLab (if needed)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you don't already have JupyterLab installed:

.. code-block:: bash

    pip install jupyterlab

Verify Installation
-------------------

To verify your installation, start JupyterLab and create a new notebook:

.. code-block:: bash

    jupyter lab

In a notebook cell, run:

.. code-block:: python

    import jdaviz
    jdaviz.show()

This should display the Jdaviz interface in your notebook.

Getting Started
---------------

See the :ref:`quickstart` guide for examples of loading data and using Jdaviz features.

Example notebooks are available in the `notebooks directory <https://github.com/spacetelescope/jdaviz/tree/main/notebooks>`_
of the Jdaviz repository.

Updating
--------

To update to the latest development version:

.. code-block:: bash

    pip install git+https://github.com/spacetelescope/jdaviz --upgrade

To update to the latest release version:

.. code-block:: bash

    pip install jdaviz --upgrade

Developer Installation
----------------------

For development work on Jdaviz itself, see the :ref:`developer documentation <dev-install>`.
