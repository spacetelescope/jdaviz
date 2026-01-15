.. _userapi-api_hints:

*********
API Hints
*********


Interactive hints showing available parameters and options for loaders and plugins.

Description
===========

API hints is a powerful feature that provides real-time Python code snippets as you interact
with the Jdaviz user interface. This helps you discover the programmatic API and learn how
to automate your workflows in Jupyter notebooks.

When API hints are enabled, you'll see code snippets appear as you:

* Select data loaders and configure load options
* Adjust plugin parameters
* Interact with viewers
* Create and modify subsets

The hints show the exact Python code needed to reproduce your UI actions programmatically,
making it easy to transition from interactive exploration to automated workflows.

UI Access
=========

.. wireframe-demo::
   :demo: loaders,loaders:api-toggle,loaders:select-tab=Viewer,save,save:api-toggle,settings,settings:api-toggle,settings:select-tab=Units,info,info:api-toggle,info:select-tab=Markers,info:select-tab=Logger,subsets,subsets:api-toggle
   :demo-repeat: true
   :show-scroll-to: true

Enabling API Hints
------------------

To enable API hints in the user interface:

1. Click the **API Hints** button in the top toolbar (notebook environments)
2. The button will highlight when API hints are active
3. Click again to toggle off

Where Hints Appear
------------------

When enabled, API hints appear in different contexts:

**Data Loaders**
  Code snippets appear showing how to access the loader and set its properties.
  For example, when using the file loader:

  .. code-block:: python

      ldr = jdaviz.loaders['file']
      ldr.filename = 'mydata.fits'
      ldr.format = '1D Spectrum'
      ldr.load()

**Plugins**
  Hints show how to access the plugin and set parameters:

  .. code-block:: python

      plugin = jdaviz.plugins['Plot Options']
      plugin.layer = 'image_label'
      plugin.image_colormap = 'Viridis'

**Data Menu**
  When selecting data in the menu, hints show how to access that data:

  .. code-block:: python

      data = jdaviz.get_data('data_label')

API Access
==========

Toggling Programmatically
-------------------------

You can enable or disable API hints from code:

.. code-block:: python

    from jdaviz import Imviz

    imviz = Imviz()
    imviz.show()

    # Enable API hints
    imviz.toggle_api_hints(enabled=True)

    # Disable API hints
    imviz.toggle_api_hints(enabled=False)

    # Toggle current state
    imviz.toggle_api_hints()

This method works with all Jdaviz configurations (Imviz, Specviz, Cubeviz, etc.).

Using the Top-Level API
-----------------------

You can also toggle API hints using the top-level ``jdaviz`` API:

.. code-block:: python

    import jdaviz

    jdaviz.show()
    jdaviz.toggle_api_hints(enabled=True)

Example Workflow
----------------

A typical workflow using API hints:

.. code-block:: python

    from jdaviz import Specviz

    # Create instance
    specviz = Specviz()
    specviz.show()

    # Enable API hints
    specviz.toggle_api_hints(enabled=True)

    # Now interact with the UI:
    # 1. Click on a loader - see the loader access code
    # 2. Select options - see how to set them
    # 3. Open a plugin - see how to access it
    # 4. Change plugin parameters - see the property setters

    # Copy the hints to build your automated workflow
    # Then disable hints when not needed
    specviz.toggle_api_hints(enabled=False)

Details
=======

Hint Format
-----------

API hints are displayed as Python code blocks showing:

* **Object access**: How to get a reference to the loader, plugin, or data
* **Property names**: The exact attribute names to use
* **Current values**: The values you've set in the UI
* **Method calls**: Any methods needed (like ``.load()`` or ``.extract()``)

The hints update dynamically as you change values in the UI.

Limitations
-----------

**Complex Interactions**
  Some complex UI interactions may not have direct API equivalents.
  In these cases, hints show the closest programmatic approach.

**State Dependencies**
  Hints show current state. Some operations may depend on previous steps
  that aren't shown in the current hint.

**Performance**
  API hints have minimal performance impact, but you may want to disable them
  when working with very large datasets or complex workflows.

Learning Path
-------------

API hints are designed to help you learn the Jdaviz API:

1. **Discover**: Use the UI and watch the hints to discover available API methods
2. **Learn**: See the relationship between UI actions and code
3. **Transition**: Copy hints into your notebook to automate workflows
4. **Master**: Build complex programmatic workflows using the patterns learned

Example Notebooks
=================

See the following notebooks for examples of using API hints:

* :doc:`../sample_notebooks` - Collection of example notebooks
* :gh-notebook:`ImvizExample.ipynb <ImvizExample>` - Imviz API examples
* :gh-notebook:`SpecvizExample.ipynb <SpecvizExample>` - Specviz API examples
* :gh-notebook:`CubevizExample.ipynb <CubevizExample>` - Cubeviz API examples

See Also
========

* :doc:`cheatsheet` - Quick reference for common API operations
* :doc:`../plugin_api` - Detailed plugin API documentation
* :doc:`../load` - Documentation on data loaders
* :doc:`show_options` - Customizing display options
