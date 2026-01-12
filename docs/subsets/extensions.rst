.. _subsets-extensions:

**********************************
Subset Extensions
**********************************

Additional subset tools and functionality provided by extensions and third-party packages.

Overview
========

Jdaviz's subset capabilities can be extended with additional tools through extensions.
These extensions provide advanced subset selection, manipulation, and analysis features.

Installing Extensions
=====================

Subset extensions are typically installed as separate Python packages:

.. code-block:: bash

    pip install jdaviz-subset-extension-name

Once installed, the subset tools will be available in jdaviz.

Available Extensions
====================

Check the `jdaviz extensions registry <https://github.com/spacetelescope/jdaviz/wiki/Extensions>`_
for a list of available subset extensions, including:

- Advanced selection tools and geometries
- Automated subset generation based on data properties
- Subset arithmetic and boolean operations
- Domain-specific selection criteria
- Subset import/export utilities

Creating Your Own Subset Extension
===================================

You can create custom subset tools by:

1. Implementing subset selection or manipulation algorithms
2. Integrating with jdaviz's subset system
3. Creating UI components if needed
4. Packaging and distributing your extension

Refer to the jdaviz developer documentation for details on creating subset extensions.

Working with Subsets Programmatically
======================================

Extensions can also provide programmatic access to advanced subset operations through
the jdaviz API. See the :ref:`subsets` documentation for information on working with
subsets in code.
