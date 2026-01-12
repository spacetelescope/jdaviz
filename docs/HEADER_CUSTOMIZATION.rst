:orphan:

Documentation Header/Navbar Customization
==========================================

The Jdaviz documentation now supports different header/navbar styles for different page types:

Page Types
----------

1. **Landing Page (index.html)**
   - Completely custom design with hidden Sphinx navbar
   - Custom wireframe, platform tabs, and installation sections
   - Full-screen immersive experience

2. **New/Modern Pages**
   - Add ``.. meta::`` directive with ``navbar_style: minimal`` at the top of RST file
   - Simplified navbar with modern styling
   - Platform context indicator (when applicable)
   - Example: ``docs/navbar_customization_example.rst``

3. **Deprecated/Legacy Pages**
   - No special metadata required
   - Retains original Sphinx navbar completely unchanged
   - Typically includes ``.. include:: ../_templates/deprecated_config_banner.rst``
   - Examples: config-specific docs (specviz/, cubeviz/, etc.)

Implementation Files
--------------------

- ``_templates/layout.html`` - Custom Jinja2 template extending pydata-sphinx-theme
- ``_static/platform-context.js`` - Platform context persistence across pages
- ``_static/jdaviz.css`` - Platform-specific CSS rules
- ``conf.py`` - Added ``templates_path = ['_templates']``

How to Mark New Pages
----------------------

Add this at the very top of your RST file:

.. code-block:: rst

   .. meta::
      :navbar_style: minimal

   Your Page Title
   ===============

   Your content here...

This will apply the modern navbar style to that page.

How Deprecated Pages Work
--------------------------

Pages with the deprecated banner keep the original navbar automatically.
No changes needed to existing files. Simply don't add the ``:navbar_style:`` metadata.

Example:

.. code-block:: rst

   .. include:: ../_templates/deprecated_config_banner.rst

   Your Legacy Page Title
   ======================

   Your content here...

Platform Context in Navbar
---------------------------

When users navigate from the landing page with a platform selection
(Desktop/MAST/Jupyter/Platform), a platform badge appears in the navbar
showing their current context. This persists across all pages.

The badge is automatically added via JavaScript in ``layout.html`` and
reads from ``sessionStorage``.

Customization
-------------

To further customize navbar behavior:

1. Edit ``_templates/layout.html`` Jinja2 blocks:
   - ``{% block header %}`` - Overall header/navbar
   - ``{% block navbar_header_items %}`` - Left side items
   - ``{% block navbar_end %}`` - Right side items

2. Add page-specific logic using:
   - ``{% if pagename == 'some-page' %}``
   - ``{% if meta and meta.get('navbar_style') == 'minimal' %}``
   - Check for deprecated banner inclusion

3. Use CSS in ``_static/jdaviz.css`` for styling:
   - ``.bd-header`` - Main header
   - ``.navbar-nav`` - Navigation items
   - ``.platform-badge`` - Platform indicator

See Also
--------

- ``platform_content_example.rst`` - Platform-specific content visibility
- ``navbar_customization_example.rst`` - Navbar customization examples
