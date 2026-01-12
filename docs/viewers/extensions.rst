.. _viewers-extensions:

**********************************
Viewer Extensions
**********************************

Additional viewers and visualization tools provided by extensions and third-party packages.

Overview
========

Jdaviz's visualization capabilities can be extended with custom viewers through extensions.
These extensions can add new types of viewers or enhance existing ones with specialized features.

Installing Extensions
=====================

Viewer extensions are typically installed as separate Python packages:

.. code-block:: bash

    pip install jdaviz-viewer-extension-name

Once installed, the new viewers will be available in jdaviz configurations.

Available Extensions
====================

Check the `jdaviz extensions registry <https://github.com/spacetelescope/jdaviz/wiki/Extensions>`_
for a list of available viewer extensions, including:

- Specialized visualization tools for specific data types
- Custom plot types and overlays
- Interactive data exploration tools
- Domain-specific visualization features

Creating Your Own Viewer Extension
===================================

You can create custom viewers by:

1. Subclassing jdaviz's base viewer classes
2. Implementing the viewer interface and event handlers
3. Packaging your viewer as a Python package
4. Registering it with jdaviz's extension system

See the :ref:`dev-extensions` documentation for details on creating custom viewers.

Integration with Configurations
================================

Custom viewers can be integrated into existing jdaviz configurations (Imviz, Specviz, etc.)
or used in custom configurations tailored to specific workflows.
