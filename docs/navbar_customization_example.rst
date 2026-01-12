:orphan:

.. meta::
   :navbar_style: minimal

New Page Example (Minimal Header)
==================================

This page demonstrates the new navbar style for non-deprecated documentation.

By adding the following metadata at the top of any RST file:

.. code-block:: rst

   .. meta::
      :navbar_style: minimal

The page will use a simplified/modern navbar instead of the legacy one.

Pages without this metadata (like the deprecated config-specific pages) will retain
the original navbar styling.

The landing page (index.html) has a completely hidden navbar for a full-screen
custom design.

Navbar Behavior
---------------

**Landing Page (index.html)**
  - Completely hidden navbar for custom full-screen design
  - Uses custom wireframe, platform tabs, and installation sections

**New Pages (with ``navbar_style: minimal``)**
  - Simplified navbar with modern styling
  - Shows platform context indicator if available
  - Can be customized further in ``_templates/layout.html``

**Deprecated Pages (no metadata)**
  - Original navbar styling unchanged
  - Includes all legacy navigation elements
  - Typically includes the deprecated_config_banner.rst

Platform Context Integration
-----------------------------

The navbar automatically displays the current platform context (if set) for
all non-landing pages. This helps users understand which platform's
documentation they're viewing.

Example platform indicators:
- Desktop
- MAST
- Jupyter
- Platform

Customizing Further
-------------------

To customize the navbar for specific pages or sections, edit the
``_templates/layout.html`` file. You can:

1. Add custom CSS for specific page patterns
2. Include/exclude specific navbar items
3. Add custom badges or indicators
4. Modify the header background or styling

See the Jinja2 template blocks in ``layout.html`` for available customization points.
