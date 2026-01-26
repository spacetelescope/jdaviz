:orphan:

Platform-Specific Content Example
===================================

This is a template showing how to mark sections as platform-specific.

Universal Content
-----------------

This content appears for all platforms.

API Access
----------

.. rst-class:: api-section

This entire section will be hidden for Desktop and MAST platforms (no API access).

You can use the ``api-section`` class on any block:

.. rst-class:: api-section

.. code-block:: python

    # This code block is hidden on desktop and MAST
    import jdaviz
    jd = jdaviz.Imviz()
    viewer = jd.default_viewer

Platform-Specific Sections
---------------------------

.. rst-class:: platform-specific
.. container::
   :name: data-platforms="jupyter,platform"

   This content only appears for Jupyter and cloud platforms.
   Great for Python API examples!

.. rst-class:: platform-specific
.. container::
   :name: data-platforms="desktop,mast"

   This content only appears for Desktop and MAST platforms.
   Great for UI-only instructions!

Usage Examples
--------------

**For API Documentation:**

.. rst-class:: api-section

Accessing the Data Menu Programmatically
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Get data menu for a specific viewer
    dm = jd.viewers['viewer-name'].data_menu

    # Toggle layer visibility
    dm.toggle_visibility('layer-name')

**For Installation:**

.. rst-class:: platform-specific
.. container::
   :name: data-platforms="jupyter"

   **Local Installation:** To install Jdaviz in your local Jupyter environment:

   .. code-block:: bash

       pip install jdaviz

.. rst-class:: platform-specific
.. container::
   :name: data-platforms="platform"

   **Cloud Platform Access:** Access Jdaviz on TIKE or Roman Science Platform - no installation needed!

.. rst-class:: platform-specific
.. container::
   :name: data-platforms="desktop"

   **Desktop Application:** Download the standalone desktop application from the installation page.

Notes
-----

- The ``api-section`` class hides content on desktop and MAST platforms
- The ``platform-specific`` class with ``data-platforms`` attribute shows content only for specified platforms
- Platform values: ``desktop``, ``mast``, ``jupyter``, ``platform``
- Multiple platforms can be specified: ``data-platforms="jupyter,platform"``
- Content visibility is controlled by [platform-context.js](/_static/platform-context.js) and [jdaviz.css](/_static/jdaviz.css)
