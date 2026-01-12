.. _loaders-extensions:

**********************************
Data Loader Extensions
**********************************

Additional data loaders provided by extensions and third-party packages.

Overview
========

Jdaviz can be extended with additional data loaders through extensions. These extensions
add support for new data sources and formats beyond the core functionality.

Installing Extensions
=====================

Extensions are typically installed as separate Python packages:

.. code-block:: bash

    pip install jdaviz-extension-name

Available Extensions
====================

Check the `jdaviz extensions registry <https://github.com/spacetelescope/jdaviz/wiki/Extensions>`_
for a list of available extensions that provide additional data loaders.

Creating Your Own Extension
============================

You can create custom data loaders for jdaviz by:

1. Creating a Python package that implements the loader interface
2. Registering your loader with jdaviz's extension system
3. Distributing your package for others to use

Refer to the jdaviz developer documentation for details on creating extensions.
