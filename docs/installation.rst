
.. _install:

Installation
============

.. note::

    ``jdaviz`` is undergoing constant development. We encourage users to always update
    to the latest version. In general, it is good practice to install the development
    version following the instructions below as full released versions may lag behind.

User Installation
-----------------

Windows-Specific Dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Some of our dependencies require C++ compilers to install properly. These are usually
included with macOS and most Linux distributions, but are not included by default in
Windows. Microsoft provides these tools as part of their
`Build Tools for Visual Studio <https://visualstudio.microsoft.com/downloads>`_, 
which can be found under "Tools for Visual Studio" towards the bottom of the page.

Create Your Local Environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Some of Jdaviz's dependencies require non-Python packages to work
(particularly the front-end stack that is part of the Jupyter ecosystem).
We recommend using `Miniconda <https://docs.conda.io/en/latest/miniconda.html>`_
to easily manage a compatible Python environment for ``jdaviz``; it should work
with most modern shells, except CSH/TCSH.

You may want to consider installing ``jdaviz`` in a new virtual or conda environment
to avoid version conflicts with other packages you may have installed, for example:

.. code-block:: bash

    conda create -n jdaviz-env python=3.9
    conda activate jdaviz-env

Pip Install
^^^^^^^^^^^

As noted above, we typically recommend installing the latest development version:

.. code-block:: bash

    pip install git+https://github.com/spacetelescope/jdaviz --upgrade

A normal install will also work by installing the latest release version:

.. code-block:: bash

    pip install jdaviz --upgrade

Common Issues
^^^^^^^^^^^^^

If you encounter problems while following these installation instructions,
please consult :ref:`known installation issues <known_issues_installation>`.

Note that ``jdaviz`` requires Python 3.9 or newer. If your ``pip`` corresponds to an older version of
Python, it will raise an error that it cannot find a valid package.

Users occasionally encounter problems running the pure ``pip`` install above. For those
using ``conda``, some problems may be resolved by pulling the following from ``conda``
instead of ``pip``:

.. code-block:: bash

    conda install bottleneck
    conda install -c conda-forge notebook
    conda install -c conda-forge jupyterlab
    conda install -c conda-forge voila

You might also want to enable the ``ipywidgets`` notebook extension, as follows:

.. code-block:: bash

    jupyter nbextension enable --py widgetsnbextension

Developer Installation
----------------------

If you wish to contribute to Jdaviz, please fork the project to your
own GitHub account. The following instructions assume your have forked
the project and have connected
`your GitHub to SSH <https://docs.github.com/en/authentication/connecting-to-github-with-ssh>`_
and ``username`` is your GitHub username. This is a one-setup setup:

.. code-block:: bash

    git clone git@github.com:username/jdaviz.git
    cd jdaviz
    git remote add upstream git@github.com:spacetelescope/jdaviz.git
    git fetch upstream main
    git fetch upstream --tags

To work on a new feature or bug-fix, it is recommended that you build upon
the latest dev code in a new branch (e.g., ``my-new-feature``).
You also need the up-to-date tags for proper software versioning:

.. code-block:: bash

    git checkout -b my-new-feature
    git fetch upstream --tags
    git fetch upstream main
    git rebase upstream/main

For the rest of contributing workflow, it is very similar to
`how to make code contribution to astropy <https://docs.astropy.org/en/latest/development/workflow/development_workflow.html>`_,
except for the change log.
If your patch requires a change log, see ``CHANGES.rst`` for examples.

To install ``jdaviz`` for development or from source in an editable mode
(i.e., changes to the locally checked out code would reflect in runtime
after you restarted the Python kernel):

.. code-block:: bash

    pip install -e .

Optionally, to enable the hot reloading of Vue.js templates, install
``watchdog``:

.. code-block:: bash

    pip install watchdog

After installing ``watchdog``, to use it, add the following to the top
of a notebook:

.. code-block:: python

    from jdaviz import enable_hot_reloading
    enable_hot_reloading()
