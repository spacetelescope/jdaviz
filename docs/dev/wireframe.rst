.. _dev-wireframe:

******************************
Wireframe Demonstration System
******************************

The wireframe demonstration system provides interactive UI mockups throughout the jdaviz documentation. This page describes the architecture, usage, and customization options for developers.

Overview
========

The wireframe system consists of three modular components:

* ``wireframe-base.html`` - HTML structure
* ``wireframe-demo.css`` - Styling and theming
* ``wireframe-controller.js`` - Interactive behavior and automation

These components are loaded via the ``wireframe-demo`` Sphinx directive, which automatically injects them into documentation pages with full configuration support.

Component Files
===============

wireframe-base.html
-------------------

Contains the complete HTML structure for the interactive wireframe, including:

* Wireframe container and toolbar with icon buttons
* Sidebar panel with tabs and content areas
* Viewer area with data visualization mockup
* Data menu popup
* Cycle control button for demonstrations

wireframe-demo.css
------------------

Contains all CSS styles for the wireframe, including:

* Layout and positioning (flexbox-based)
* Color schemes and theming (dark/light mode support)
* Responsive design with media queries
* Smooth animations and transitions
* Component-specific styles for toolbar, sidebars, viewer, expansion panels
* Special styling for plugins sidebar with accordion UI

**Key Features:**

* Uses ``:has()`` selector for conditional styling (e.g., removing padding when expansion panels are present)
* CSS variables for easy theme customization
* Smooth transitions for panel expansions (0.3s ease)
* Hover states and interactive feedback

wireframe-controller.js
-----------------------

Contains all JavaScript functionality using ES5 syntax:

* **Auto-cycling** - Demonstrates sidebars in sequence with configurable timing
* **Sidebar management** - Dynamically generates content from registry or custom sources
* **Expansion panels** - Accordion-style panels for plugins sidebar (5 panels)
* **Demo actions** - Supports actions like ``open-panel``, ``select-data``, ``select-tab``
* **Timing control** - Custom per-step delays using ``@delay`` syntax
* **Repeat control** - Demos can loop continuously or stop after one cycle
* **API snippets** - Toggleable code examples for each feature
* **Interactive controls** - Pause/resume, manual sidebar selection

Usage
=====

Basic Directive
---------------

To embed a wireframe in any RST file, use the ``wireframe-demo`` directive:

.. code-block:: rst

   .. wireframe-demo::

This creates a default wireframe with standard auto-cycling behavior.

Configuration Options
=====================

The directive supports extensive customization through options:

demo
----

**Type:** string

**Default:** ``'loaders,save,settings,info,plugins,subsets'``

Defines the demo sequence - which sidebars to show and what actions to perform.

**Simple sidebar list:**

.. code-block:: rst

   .. wireframe-demo::
      :demo: plugins,subsets,info

**Actions with timing:**

.. code-block:: rst

   .. wireframe-demo::
      :demo: plugins,plugins@1000:open-panel,plugins:select-data=Image 2

**Action Syntax:**

* ``sidebar`` - Show the sidebar
* ``sidebar:action`` - Perform an action on the sidebar
* ``sidebar:action=value`` - Perform an action with a parameter
* ``sidebar@delay:action`` - Add custom timing (in milliseconds) before the action
* ``:action`` or ``:action=value`` - Standalone action (no sidebar required)

**Available Actions:**

* ``open-panel`` - Opens the expansion panel in plugins sidebar
* ``select-tab=<name>`` - Switches to a specific tab in multi-tab sidebars
* ``select-dropdown=<label>:<value>`` - Selects a dropdown value (case-insensitive matching)
* ``api-toggle`` - Toggles API mode on/off
* ``open-data-menu`` - Opens the data menu popup (standalone action)
* ``highlight=<selector>`` - Highlights element(s) matching CSS selector (standalone action)

enable-only
-----------

**Type:** string (comma-separated)

**Default:** All sidebars enabled

Restricts which toolbar buttons can be clicked by users. Other buttons appear disabled.

.. code-block:: rst

   .. wireframe-demo::
      :enable-only: plugins
      :demo: plugins

To disable all sidebar buttons (e.g., for standalone action demos):

.. code-block:: rst

   .. wireframe-demo::
      :enable-only:
      :demo: open-data-menu

initial
-------

**Type:** string (comma-separated)

**Default:** First sidebar in demo sequence

Sets which sidebar(s) are visible when the wireframe first loads, before the demo starts.

.. code-block:: rst

   .. wireframe-demo::
      :initial: loaders,plugins
      :demo: save,settings

This is useful to show a specific starting state that differs from the demo sequence.

show-scroll-to
--------------

**Type:** boolean

**Default:** ``false``

Controls visibility of "Learn more" scroll-to buttons in sidebar descriptions.

.. code-block:: rst

   .. wireframe-demo::
      :show-scroll-to: true

demo-repeat
-----------

**Type:** boolean

**Default:** ``true``

Controls whether the demo loops continuously or stops after one cycle.

.. code-block:: rst

   .. wireframe-demo::
      :demo-repeat: false

When set to ``false``, the demo plays once and shows a restart button.

plugin-name
-----------

**Type:** string

**Default:** ``'Data Analysis Plugin'``

Sets the name of the plugin in the expansion panel header.

.. code-block:: rst

   .. wireframe-demo::
      :plugin-name: Aperture Photometry

plugin-panel-opened
-------------------

**Type:** boolean

**Default:** ``true``

Controls whether the plugin expansion panel is open by default.

.. code-block:: rst

   .. wireframe-demo::
      :plugin-panel-opened: false

custom-content
--------------

**Type:** string

**Default:** Auto-generated from registry

Provides custom HTML content for sidebars. Overrides the default content from the registry.

**Format:** ``sidebar=content`` or ``sidebar:tab=content``

.. code-block:: rst

   .. wireframe-demo::
      :custom-content: plugins=<div class="wireframe-description">Custom content</div>

Complete Example
================

Here's a complete example from a plugin documentation page:

.. code-block:: rst

   .. _plugins-aperture_photometry:

   ********************
   Aperture Photometry
   ********************

   .. wireframe-demo::
      :demo: plugins,plugins@1000:open-panel,plugins:select-dropdown=Data:Image 2,plugins@3000:highlight=.wireframe-form-group:has(#data-select)
      :enable-only: plugins
      :plugin-name: Aperture Photometry
      :plugin-panel-opened: false
      :demo-repeat: false

   .. plugin-availability::

   This plugin performs aperture photometry...

This configuration:

1. Shows only the plugins sidebar
2. After 1 second, opens the expansion panel
3. Selects "Image 2" from the Data dropdown
4. After 3 seconds, highlights the Data dropdown group
5. Only allows clicking on the plugins button
6. Names the panel "Aperture Photometry"
7. Panel starts closed
8. Demo runs once and stops (highlight persists since it's the last step)

Advanced Demo Actions
=====================

select-dropdown
---------------

**Syntax:** ``sidebar:select-dropdown=<label>:<value>``

Selects a value from a dropdown menu. Both label and value matching are case-insensitive.

.. code-block:: rst

   .. wireframe-demo::
      :demo: loaders,loaders:select-dropdown=Source:file,loaders:select-dropdown=Format:1D Spectrum

The action will:

1. Find dropdowns by their label text (case-insensitive)
2. Match the value against option text (case-insensitive)
3. Set the selected value
4. Trigger a change event

**Example:** ``select-dropdown=data:image 2`` matches label "Data" and selects option "Image 2"

highlight
---------

**Syntax:** ``sidebar@duration:highlight=<selector>`` or ``:highlight=<selector>``

Highlights one or more elements using a CSS selector. This is a standalone action that doesn't require a sidebar.

.. code-block:: rst

   .. wireframe-demo::
      :demo: loaders,loaders:select-tab=Data,loaders@3000:highlight=#source-select
      :demo-repeat: false

The highlight:

* Uses an animated orange pulsing glow effect
* Lasts for the step's duration (specified by ``@duration`` syntax)
* Clears when moving to the next step
* **Persists** if it's the last step and ``demo-repeat: false``
* Can target multiple elements with a single selector

**Common selectors:**

* ``#element-id`` - Highlight by ID
* ``.class-name`` - Highlight by class
* ``select[name="source"]`` - Highlight specific form element
* ``.wireframe-form-group:has(#data-select)`` - Highlight parent container

open-data-menu
--------------

**Syntax:** ``:open-data-menu``

Opens the data menu popup. This is a standalone action that doesn't require a sidebar to be active.

.. code-block:: rst

   .. wireframe-demo::
      :demo: open-data-menu
      :enable-only:
      :demo-repeat: false

Useful for focusing on the data menu functionality without showing sidebar content.

api-toggle
----------

**Syntax:** ``sidebar:api-toggle``

Toggles the API mode on or off for the current sidebar view.

.. code-block:: rst

   .. wireframe-demo::
      :demo: loaders,loaders@2000:api-toggle

Standalone Actions
------------------

Some actions can be used without activating a sidebar first:

* ``open-data-menu`` - Opens data menu popup
* ``highlight=<selector>`` - Highlights elements

Use these with ``:enable-only:`` to create focused demos:

.. code-block:: rst

   .. wireframe-demo::
      :demo: open-data-menu,highlight=#data-format-select
      :enable-only:
      :demo-repeat: false

Content Registry System
=======================

The ``WIREFRAME_CONTENT_REGISTRY`` in ``docs/conf.py`` (lines 1166-1390) defines structured data for automatic content generation.

Registry Structure
------------------

The registry is a nested dictionary with three types of entries:

**Simple sidebars with form elements:**

.. code-block:: python

   'settings': {
       'form_elements': [
           {
               'type': 'select',
               'label': 'Theme',
               'options': ['Light', 'Dark', 'Auto']
           },
           {
               'type': 'checkbox',
               'label': 'Show tooltips'
           },
           {
               'type': 'button',
               'label': 'Apply Settings'
           }
       ]
   }

**Sidebars with tabs:**

.. code-block:: python

   'info': {
       'tabs': ['File Info', 'Display Options'],
       'tab_content': {
           'File Info': {
               'form_elements': [...]
           },
           'Display Options': {
               'form_elements': [...]
           }
       }
   }

**Plugins sidebar:**

.. code-block:: python

   'plugins': {
       'Aperture Photometry': {
           'form_elements': [
               {
                   'type': 'select',
                   'label': 'Data',
                   'options': ['Image 1', 'Image 2']
               },
               {
                   'type': 'input',
                   'label': 'Radius',
                   'placeholder': '5.0'
               }
           ]
       },
       'Model Fitting': {
           'form_elements': [...]
       }
   }

Currently, 16 plugins are defined in the registry:

* Aperture Photometry
* Line Analysis
* Model Fitting
* Catalog Search
* Collapse
* Gaussian Smooth
* Moment Maps
* Spectral Extraction
* Data Quality
* Ramp Extraction
* Compass
* Footprints
* Orientation
* Line Lists
* Slit Overlay
* Sonify Data

Supported Element Types
-----------------------

``select``
  Dropdown menu with options array

``input``
  Text input field with optional placeholder

``checkbox``
  Checkbox with label

``button``
  Action button with label

Auto-generation Functions
--------------------------

``generate_form_html(form_elements)``
  Converts element dictionaries to HTML strings. Automatically generates IDs for select elements based on their labels (e.g., label "Source" becomes ID ``source-select``).

``generate_content_for_sidebar(sidebar_type, plugin_name=None)``
  Generates complete sidebar content from registry

  * Handles tabs, plugins, and simple sidebars
  * Returns dictionary with tab keys or single 'main' key

Form Element IDs
----------------

Select elements are automatically assigned IDs based on their label text:

* Label: "Source" → ID: ``source-select``
* Label: "Data Format" → ID: ``data-format-select``
* Label: "Viewer Type" → ID: ``viewer-type-select``

These IDs are useful for targeting elements with the ``highlight`` action:

.. code-block:: rst

   :demo: loaders,loaders@3000:highlight=#source-select

JavaScript Integration
======================

Demo Parsing
------------

The JavaScript controller parses demo strings using ``indexOf`` and ``substring`` to handle:

* Timing: ``@1000`` extracts 1000ms delay
* Actions: ``:open-panel`` identifies the action
* Values: ``=Image 2`` preserves spaces in parameter values

Demo Sequence Storage
---------------------

Parsed demos are stored as:

.. code-block:: javascript

   demoSequence = [
       {sidebar: 'plugins', delay: 2000},
       {sidebar: 'plugins', action: 'open-panel', delay: 1000},
       {sidebar: 'plugins', action: 'select-data', value: 'Image 2', delay: 2000}
   ]

Auto-cycling Logic
------------------

The ``autoCycleSidebars()`` function:

1. Iterates through demoSequence
2. Applies custom delays from each step
3. Checks ``demoRepeat`` at completion
4. Either loops back to start or shows restart button

Landing Page vs. Documentation Pages
=====================================

**Landing Page (index.html):**

* Loads components via ``fetch()`` calls
* Processes Jinja2 variables with JavaScript string replacement
* Uses ``_static`` directory for assets
* No Sphinx directive involved

**Documentation Pages (RST files):**

* Uses ``.. wireframe-demo::`` directive
* Sphinx processes Jinja2 variables at build time
* Components embedded directly in HTML output
* Supports all configuration options

Asset Copying
=============

The ``copy_wireframe_assets()`` function in ``conf.py`` handles asset preparation for the landing page:

1. Copies ``wireframe-demo.css`` directly to ``_static``
2. Processes ``wireframe-base.html`` and ``wireframe-controller.js``
3. Replaces ``{{ jdaviz_version }}`` template variable
4. Replaces ``{{ descriptions.* }}`` variables with proper escaping
5. Handles ``|capitalize`` Jinja2 filter

Adding New Plugins
==================

To add a new plugin to the wireframe system:

1. **Add to Registry** (``docs/conf.py``):

   .. code-block:: python

      'plugins': {
          # ... existing plugins ...
          'New Plugin Name': {
              'form_elements': [
                  {'type': 'select', 'label': 'Input Data', 'options': ['Data 1', 'Data 2']},
                  {'type': 'input', 'label': 'Parameter', 'placeholder': '1.0'},
                  {'type': 'button', 'label': 'Execute'}
              ]
          }
      }

2. **Create Plugin Doc** (``docs/plugins/new_plugin.rst``):

   .. code-block:: rst

      .. _plugins-new_plugin:

      **********
      New Plugin
      **********

      .. wireframe-demo::
         :demo: plugins,plugins@1000:open-panel
         :enable-only: plugins
         :plugin-name: New Plugin Name
         :plugin-panel-opened: false
         :demo-repeat: false

3. **Build and Test:**

   .. code-block:: bash

      cd docs
      make html
      open _build/html/plugins/new_plugin.html

Benefits and Design Principles
===============================

Modularity
----------

Each component (HTML, CSS, JS) is in its own file, making updates straightforward.

Maintainability
---------------

Registry-based approach eliminates duplicate HTML strings across 16+ plugin pages. Single source of truth for plugin forms.

Reusability
-----------

Same components used in landing page and documentation pages with different loading mechanisms.

Automation
----------

Auto-generation reduces manual work. Adding a plugin requires only registry entry, not HTML authoring.

Reduced File Size
-----------------

``index.html`` reduced from 3382 to 967 lines by extracting components.

Accessibility Considerations
=============================

Current implementation includes:

* Keyboard-accessible buttons
* Semantic HTML structure
* Clear visual feedback for interactions

Future enhancements could include:

* ARIA labels for screen readers
* Focus management for sidebar transitions
* Keyboard navigation for expansion panels
* High contrast mode support

Technical Details
=================

Jinja2 Variable Handling
-------------------------

Variables like ``{{ jdaviz_version }}`` and ``{{ descriptions.* }}`` are:

* Replaced by Sphinx at build time for RST pages
* Replaced by JavaScript string operations for landing page
* Properly escaped for HTML and JavaScript contexts

Sidebar Content Management
--------------------------

Content flows through three paths:

1. **Registry auto-generation** - Default for known sidebars/plugins
2. **Custom content option** - Override via ``:custom-content:``
3. **Fallback** - Simple "description coming soon" messages

The directive prioritizes: custom-content → registry → fallback

File Paths
----------

* Source files: ``docs/_templates/wireframe-*.{html,css,js}``
* Build output: ``docs/_build/html/_static/wireframe-*.{html,css,js}``
* Landing page loads from: ``_static/`` or ``_templates/``

Demo Timing Examples
====================

The ``@delay`` syntax controls how long each step lasts:

**Default timing (2 seconds per step):**

.. code-block:: rst

   :demo: loaders,save,settings

Each sidebar shows for 2 seconds before moving to the next.

**Custom timing:**

.. code-block:: rst

   :demo: loaders@1000,save@3000,settings@5000

Shows loaders for 1 second, save for 3 seconds, settings for 5 seconds.

**Actions with timing:**

.. code-block:: rst

   :demo: plugins,plugins@1000:open-panel,plugins@3000:select-dropdown=Data:Image 2

1. Show plugins sidebar (2s default)
2. Wait 1 second, open panel
3. Wait 3 seconds, select dropdown value

**Highlight with timing:**

.. code-block:: rst

   :demo: loaders,loaders:select-tab=Data,loaders@3000:highlight=#source-select
   :demo-repeat: false

The highlight will:

* Appear after the select-tab action completes
* Last for 3 seconds (the step duration)
* Remain visible since it's the last step with no repeat

**Timing tips:**

* First appearance of a sidebar uses default or specified timing
* Actions on the same sidebar don't re-show it (only perform the action)
* Highlights clear on next step unless it's the final step with ``demo-repeat: false``
* Use longer durations (3000-5000ms) for complex actions users should observe

Troubleshooting
===============

Demo not starting
-----------------

* Check ``:demo:`` option syntax
* Verify JavaScript console for errors
* Ensure sidebar names match available options
* For standalone actions, use ``:enable-only:`` to disable all sidebars

Content not appearing
---------------------

* Verify plugin name matches registry key exactly
* Check ``:plugin-name:`` spelling
* Inspect browser console for JSON parsing errors

Panel not opening
-----------------

* Ensure action is ``open-panel`` not ``open_panel``
* Check timing: use ``@delay`` syntax correctly
* Verify ``plugin-panel-opened`` is set appropriately

Dropdown not selecting
----------------------

* Use correct syntax: ``select-dropdown=Label:Value``
* Check that label and value match dropdown content (case-insensitive)
* Ensure dropdown ID follows pattern (e.g., ``#source-select`` for "Source" label)
* Verify dropdown is populated before action executes

Highlight not appearing
-----------------------

* Verify CSS selector is valid and matches elements within the wireframe container
* Check browser console for querySelector errors
* Use browser dev tools to test selectors
* Common selectors: ``#id``, ``.class``, ``select[name="field"]``

Highlight disappearing too soon
-------------------------------

* Highlight clears on each new step
* To persist: make it the last step and set ``:demo-repeat: false``
* Increase step duration with ``@delay`` syntax

Data menu not opening
---------------------

* Use ``:open-data-menu`` (with colon prefix for standalone action)
* Or use ``sidebar:open-data-menu`` to trigger from a sidebar context
* Ensure data menu trigger button exists in wireframe

Future Enhancements
===================

Potential improvements:

* Additional demo actions (close-panel, hover-over, etc.)
* Mobile-optimized wireframes with touch gestures
* Keyboard navigation shortcuts
* Enhanced accessibility features
* Support for custom toolbar icons
* Integration with actual Vue component previews
* Recording and playback of user interactions

See Also
========

* :doc:`ui_style_guide` - UI design guidelines
* :ref:`dev-new-plugin` - Creating new plugins
* :doc:`infrastructure` - Build and deployment
