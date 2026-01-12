.. _plugins-extensions:

**********************************
Plugin Extensions
**********************************

Additional analysis plugins provided by extensions and third-party packages.

Overview
========

Jdaviz's analysis capabilities can be extended with additional plugins through extensions.
These plugins provide specialized analysis tools for various astronomical use cases.

Installing Extensions
=====================

Plugin extensions are typically installed as separate Python packages:

.. code-block:: bash

    pip install jdaviz-plugin-extension-name

Once installed, the plugins will automatically appear in the jdaviz interface.

Available Extensions
====================

Check the `jdaviz extensions registry <https://github.com/spacetelescope/jdaviz/wiki/Extensions>`_
for a list of available plugin extensions, including:

- Specialized analysis tools for specific instruments
- Advanced fitting and modeling plugins
- Custom visualization and processing tools
- Domain-specific analysis workflows

Creating Your Own Plugin Extension
===================================

You can create custom analysis plugins by:

1. Implementing the plugin interface using jdaviz's plugin API
2. Packaging your plugin as a Python package
3. Registering it with jdaviz's extension system
4. Distributing it to the community

See the :ref:`plugin-apis` documentation for details on creating plugin extensions.
