.. _userapi-api_hints:
.. rst-class:: section-icon-mdi-code-tags

*********
API Hints
*********


Enabling API hints updates the UI to show API code snippets instructing how to reproduce the
same actions and state in the API that are currently seen in the UI.  This can be a very
useful way to create simple reproducible workflows or to extend workflows done in the UI
to batch processing in notebooks.

When API hints are enabled, you'll see code snippets appear as you:

* Select data loaders and configure load options
* Adjust plugin parameters
* Interact with viewers
* Create and modify subsets

UI Access
=========

To enable API hints in the user interface:

1. Click the **API Hints** button in the top toolbar (notebook environments)
2. The button will highlight when API hints are active
3. Click again to toggle off

.. wireframe-demo::
   :demo: loaders,loaders:api-toggle,loaders:select-tab=Viewer,save,save:api-toggle,settings,settings:api-toggle,settings:select-tab=Units,info,info:api-toggle,info:select-tab=Markers,info:select-tab=Logger,subsets,subsets:api-toggle
   :demo-repeat: true

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

      plg = jdaviz.plugins['Plot Options']
      plg.layer = 'image_label'
      plg.image_colormap = 'Viridis'

**Data Menu**
  When selecting data in the menu, hints show how to access that data:

  .. code-block:: python

      dm = jdaviz.viewers['1D Spectrum'].data_menu

API Access
==========

Toggling Programmatically
-------------------------

You can enable or disable API hints from code:

.. code-block:: python

    import jdaviz as jd

    jd.show()

    # Enable API hints
    jd.toggle_api_hints(enabled=True)

    # Disable API hints
    jd.toggle_api_hints(enabled=False)

    # Toggle current state
    jd.toggle_api_hints()
