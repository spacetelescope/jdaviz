.. _dev-wireframe:

******************************
Wireframe Demonstration System
******************************

The wireframe demonstration system provides interactive UI mockups throughout the jdaviz documentation. This page describes the architecture, usage, and customization options for developers.

Overview
========

The wireframe system is provided by the ``docs-wireframe-demo`` Sphinx extension
(see ``pyproject.toml``) and consists of:

* ``wireframe-base.html`` — jdaviz's HTML structure (in ``docs/_templates/``)
* ``wireframe-demo.css`` — jdaviz's styling and theming (in ``docs/_templates/``)
* ``wireframe-engine.js`` — Generic interactive engine (bundled in the extension, not overridable)

The HTML and CSS live in ``docs/_templates/`` and are loaded as jdaviz-specific overrides
of the defaults bundled in the ``docs-wireframe-demo`` package.  The engine JS is always
loaded from the package.  All three are injected inline by the ``wireframe-demo`` directive.

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

wireframe-engine.js
-------------------

The generic interactive JS engine is bundled in the ``docs-wireframe-demo`` package
(``docs_wireframe_demo/_static/wireframe-engine.js``) and is never overridden by jdaviz.
It provides:

* **Auto-cycling** — Demonstrates sidebars in sequence with configurable timing
* **Sidebar management** — Shows/hides pre-rendered panels defined in the HTML
* **Expansion panels** — Accordion-style panels for the plugins sidebar
* **Demo actions** — Supports actions like ``open-panel``, ``select-tab``, ``select-dropdown``
* **Timing control** — Custom per-step delays using ``@delay`` syntax
* **Repeat control** — Demos can loop continuously or stop after one cycle
* **Multi-viewer layouts** — Dynamic viewer splitting, images, legends, and tool toggles
* **Interactive controls** — Pause/resume, manual sidebar selection

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
* ``sidebar@duration:action`` - Specify how long this step lasts before proceeding (in milliseconds)
* ``sidebar@duration!:action`` - Same as above but **skip highlighting** the affected element
* ``:action`` or ``:action=value`` - Standalone action (no sidebar required)

The ``!`` suffix after the duration disables the highlight animation for that step.
This is useful when you want to set initial state without drawing attention to the change:

.. code-block:: rst

   # Normal: briefly highlights the dropdown after selection
   loaders@1500:select-dropdown=Source:file

   # No highlight: selects the value quietly without visual emphasis
   loaders@0!:select-dropdown=Format:1D Spectrum

**Available Actions:**

* ``open-panel`` - Opens the expansion panel in plugins sidebar
* ``select-tab=<name>`` - Switches to a specific tab in multi-tab sidebars
* ``select-dropdown=<label>:<value>`` - Selects a dropdown value (case-insensitive matching)
* ``click-button=<text>`` - Clicks a button by its text content (case-insensitive)
* ``toggle-class=<classname>`` - Toggles a CSS class on the matched element
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

Sets the name of the plugin in the expansion panel header (substituted into
``{{ plugin_name }}`` in ``wireframe-base.html``).

.. code-block:: rst

   .. wireframe-demo::
      :plugin-name: Aperture Photometry

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
7. Demo runs once and stops (highlight persists since it's the last step)

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
* Lasts for the step's duration (the ``@duration`` value specifies how long to wait before proceeding)
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

click-button
------------

**Syntax:** ``sidebar:click-button=<text>``

Clicks a button by its text content (case-insensitive matching). Provides visual feedback with a brief highlight.

.. code-block:: rst

   .. wireframe-demo::
      :demo: loaders,loaders@1000:click-button=Load

This is useful for demonstrating form submission workflows:

.. code-block:: rst

   .. wireframe-demo::
      :demo: loaders,loaders:select-dropdown=source:file,loaders:select-dropdown=format:image,loaders@1000:click-button=Load

toggle-class
------------

**Syntax:** ``selector:toggle-class=<classname>``

Toggles a CSS class on the element(s) matched by a CSS selector.  Because this is a CSS
selector step, the selector must start with ``#``, ``.``, or ``[``.

.. code-block:: rst

   .. wireframe-demo::
      :demo: loaders,.api-button:toggle-class=active
      :demo-repeat: true

This is used to implement the **API Hints toggle**: clicking ``.api-button`` toggles its
``active`` class, which via CSS (``':has(.api-button.active)'``) shows or hides
``.api-snippet-container`` elements inside each sidebar panel.

**Example — cycling API hints on/off across sidebars:**

.. code-block:: rst

   .. wireframe-demo::
      :demo: loaders,.api-button:toggle-class=active,save,.api-button:toggle-class=active
      :demo-repeat: true

Each ``.api-button:toggle-class=active`` flips the button state: the first call turns
API snippets on, the second turns them off.

Standalone Actions
------------------

Some actions can be used without activating a sidebar first:

* ``pause`` - Waits without performing any action
* ``open-data-menu`` - Opens data menu popup
* ``highlight=<selector>`` - Highlights elements

pause
^^^^^

**Syntax:** ``pause@duration``

Pauses the demo for the specified duration without performing any action.
Useful for adding delays between actions or giving the user time to observe the current state.

.. code-block:: rst

   .. wireframe-demo::
      :demo: loaders,pause@3000,settings
      :demo-repeat: false

Use these with ``:enable-only:`` to create focused demos:

.. code-block:: rst

   .. wireframe-demo::
      :demo: open-data-menu,highlight=#data-format-select
      :enable-only:
      :demo-repeat: false

Multi-Viewer Actions
====================

The wireframe supports dynamic multi-viewer layouts through special viewer actions.
These actions can be used in both ``:initial:`` and ``:demo:`` options.

Viewer Action Syntax
--------------------

Viewer actions use the format: ``viewer-action@duration:param1:param2:param3``

The ``@duration`` specifies how long (in milliseconds) to wait after performing this action before proceeding to the next step. Use ``@0`` for immediate transitions.

Available viewer actions:

viewer-add
^^^^^^^^^^

**Syntax:** ``viewer-add@duration:direction:newId`` or ``viewer-add@duration:direction:newId:parentId``

Splits an existing viewer and adds a new one.

**Parameters:**

* ``direction`` - Split direction: ``horiz``, ``h``, ``vert``, ``v``, ``horiz-before``, ``hb``, ``vert-before``, ``vb``
* ``newId`` - Unique identifier for the new viewer
* ``parentId`` (optional) - ID of viewer to split. Defaults to the last added viewer.

.. code-block:: rst

   .. wireframe-demo::
      :demo: viewer-add@1000:horiz:spectrum,viewer-add@1000:vert:cube:default

This creates:

1. Splits horizontally, adds "spectrum" viewer on the right
2. Splits the "default" viewer vertically, adds "cube" viewer below it

viewer-image
^^^^^^^^^^^^

**Syntax:** ``viewer-image@duration:viewerId:imagePath``

Sets a background image for a viewer.

**Parameters:**

* ``viewerId`` - ID of the target viewer
* ``imagePath`` - Path to the image (relative to _static or absolute URL)

.. code-block:: rst

   .. wireframe-demo::
      :initial: viewer-image@0:default:cosmic_cliffs.png
      :demo: loaders

viewer-legend
^^^^^^^^^^^^^

**Syntax:** ``viewer-legend@duration:viewerId:layer1|layer2|layer3``

Sets the legend layers displayed in a viewer. Layers are pipe-separated (``|``).

**Parameters:**

* ``viewerId`` - ID of the target viewer
* ``layers`` - Pipe-separated list of layer names

.. code-block:: rst

   .. wireframe-demo::
      :initial: viewer-legend@0:default:MIRI Image|Subset 1
      :demo: plugins

Layer icons are automatically assigned based on layer name:

* Names containing "spectrum", "1d", "2d" get spectrum icon
* Names containing "image", "miri", "nircam" get image icon
* Names containing "cube", "3d" get cube icon
* Names containing "subset" get subset icon

viewer-focus
^^^^^^^^^^^^

**Syntax:** ``viewer-focus@duration:viewerId``

Visually emphasizes a viewer with a highlighted border.

.. code-block:: rst

   .. wireframe-demo::
      :demo: viewer-add@1000:horiz:spectrum,viewer-focus@500:spectrum

viewer-remove
^^^^^^^^^^^^^

**Syntax:** ``viewer-remove@duration:viewerId``

Removes a viewer and collapses the split container if only one viewer remains.

.. code-block:: rst

   .. wireframe-demo::
      :demo: viewer-add@1000:horiz:spectrum,viewer-remove@2000:spectrum

viewer-tool-toggle
^^^^^^^^^^^^^^^^^^

**Syntax:** ``viewer-tool-toggle@duration:viewerId:toolName``

Activates a tool in the viewer's toolbar, showing it as selected.

**Parameters:**

* ``viewerId`` - ID of the viewer to modify
* ``toolName`` - Name of the tool to activate. Available tools:
   * ``home`` - Home/reset view
   * ``panzoom`` (or ``pan-zoom``, ``pan_zoom``) - Pan and zoom tool
   * ``rectroi`` (or ``rect-roi``, ``rectangle``) - Rectangular ROI/subset tool
   * ``circroi`` (or ``circ-roi``, ``circle``, ``subset``) - Circular ROI/subset tool

.. code-block:: rst

   .. wireframe-demo::
      :demo: viewer-tool-toggle@1000:default:panzoom,viewer-tool-toggle@1500:default:circroi
      :demo-repeat: false

Complete Multi-Viewer Example
-----------------------------

Here's a complete example showing a multi-viewer demo:

.. code-block:: rst

   .. wireframe-demo::
      :initial: viewer-image@0:default:cosmic_cliffs.png,viewer-legend@0:default:MIRI Image|Subset 1
      :demo: viewer-add@2000:horiz:spectrum,viewer-legend@0:spectrum:1D Spectrum|Subset 1,viewer-focus@500:spectrum,plugins
      :demo-repeat: false

This configuration:

1. **Initial state**: Sets cosmic_cliffs.png as background for default viewer with two legend layers
2. **Demo step 1**: After 2 seconds, splits horizontally and adds "spectrum" viewer
3. **Demo step 2**: Immediately sets legend layers for spectrum viewer
4. **Demo step 3**: After 500ms, focuses the spectrum viewer
5. **Demo step 4**: Shows the plugins sidebar

Layout Examples
---------------

**Side-by-side viewers (1x2):**

.. code-block:: rst

   :demo: viewer-add@1000:horiz:right

**Stacked viewers (2x1):**

.. code-block:: rst

   :demo: viewer-add@1000:vert:bottom

**2x2 grid:**

.. code-block:: rst

   :demo: viewer-add@500:horiz:right,viewer-add@500:vert:bottom-left:default,viewer-add@500:vert:bottom-right:right

**L-shaped layout:**

.. code-block:: rst

   :demo: viewer-add@500:horiz:right,viewer-add@500:vert:bottom:default

Using Viewer Actions in index.html
----------------------------------

For the landing page (index.html), which doesn't use the Sphinx directive, configure
viewer actions via ``window.wireframeConfig``:

.. code-block:: javascript

   window.wireframeConfig = {
       showScrollTo: true,
       initialState: [
           "viewer-add@0:horiz:imageviewer",
           "viewer-image@0:imageviewer:_static/cosmic_cliffs.png",
           "viewer-legend@0:imageviewer:MIRI Image|Subset 1"
       ],
       customDemo: [
           "viewer-add@2000:horiz:spectrum",
           "viewer-legend@0:spectrum:1D Spectrum",
           "loaders"
       ],
       demoRepeat: true
   };

Note: ``initialState`` and ``customDemo`` are arrays of action strings, matching the
comma-separated format used in the directive. Viewers must be explicitly added using
``viewer-add`` actions before they can be configured with images or legends.

Landing Page vs. Documentation Pages
=====================================

**Landing Page (index.html):**

* Loads ``wireframe-base.html`` dynamically via ``wireframe-loader.js``
* Variables substituted at page load via JavaScript string replacement
* Uses ``_templates/`` directory for assets
* No Sphinx directive involved; configure via ``window.wireframeConfig``

**Documentation Pages (RST files):**

* Uses ``.. wireframe-demo::`` directive
* All three assets (HTML, CSS, engine JS) embedded inline at build time
* Sphinx substitutes ``wireframe_variables`` before embedding
* Supports all directive options (``initial``, ``demo``, ``enable-only``, etc.)

Asset Copying
=============

The ``copy_wireframe_assets()`` build hook (in the ``docs-wireframe-demo`` package) copies
``api.svg`` to ``_static/`` in the Sphinx output directory so the CSS can reference it.
The ``wireframe-base.html``, ``wireframe-demo.css``, and ``wireframe-engine.js`` are all
embedded inline by the directive — they are not copied as separate static files.

Adding New Plugin Documentation
================================

To add wireframe support for a new plugin page:

1. **Edit the plugins panel in** ``docs/_templates/wireframe-base.html``:

   The plugins sidebar uses expansion panels.  The first panel shows the featured plugin;
   the others are placeholder/disabled panels.  Update the first panel's content for your
   plugin, or add a new expansion panel if needed:

   .. code-block:: html

      <div class="expansion-panel" data-panel-index="0">
          <div class="expansion-panel-header">
              <span class="expansion-panel-title">{{ plugin_name }}</span>
              <span class="expansion-panel-arrow">▼</span>
          </div>
          <div class="expansion-panel-content">
              {{ descriptions.plugins|capitalize }}.
          </div>
      </div>

   The ``{{ plugin_name }}`` placeholder is substituted per-directive via ``:plugin-name:``,
   so no HTML change is needed for different plugin pages.

2. **Create the plugin doc** (``docs/plugins/new_plugin.rst``):

   .. code-block:: rst

      .. _plugins-new_plugin:

      **********
      New Plugin
      **********

      .. wireframe-demo::
         :demo: plugins,plugins@1000:open-panel
         :enable-only: plugins
         :plugin-name: New Plugin Name
         :demo-repeat: false

3. **Build and verify:**

   .. code-block:: bash

      cd docs
      make html
      open _build/html/plugins/new_plugin.html

Benefits and Design Principles
===============================

Modularity
----------

Each component (HTML, CSS, JS) is in its own file, making updates straightforward.
The engine JS is separate from the app-specific HTML/CSS, so jdaviz can change its
templates without touching the demo infrastructure.

Maintainability
---------------

Sidebar content is authored once in ``wireframe-base.html``; the engine targets it by
``data-sidebar-panel`` names.  Adding a new sidebar panel requires only HTML edits, not
changes to the directive or engine.

Reusability
-----------

The same ``wireframe-base.html`` and ``wireframe-demo.css`` are used for both the landing
page and all documentation pages via ``wireframe-loader.js`` and the Sphinx directive
respectively.

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

All sidebar content is defined statically in ``docs/_templates/wireframe-base.html``.
Template variables (``{{ descriptions.* }}``, ``{{ plugin_name }}``, etc.) are substituted
at build time from the ``wireframe_variables`` dict in ``docs/conf.py`` and the
``:plugin-name:`` directive option.

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

* Check ``:plugin-name:`` spelling matches what you expect in the panel header
* Verify ``wireframe_variables`` in ``docs/conf.py`` has the expected description keys
* Inspect browser console for JSON parsing errors

Panel not opening
-----------------

* Ensure action is ``open-panel`` not ``open_panel``
* Check timing: use ``@delay`` syntax correctly
* Use ``plugins@0:open-panel`` in ``:initial:`` to start with the panel open

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
