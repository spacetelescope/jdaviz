.. _plugin-apis:

*********************
Accessing Plugin APIs
*********************

Each plugin object is wrapped by a public user API which enables interacting with the plugin from
the notebook directly.  The plugin API object for each plugin is accessible through ``viz.plugins``.
For example:

.. code-block:: python

  plugin = viz.plugins['Plot Options']
  plugin.open_in_tray()
  plugin.show('popout')

When running in a notebook, some plugins provide API hints directly in the UI.  To enable these, toggle the ``<>`` button on the top bar of the app or call:

.. code-block:: python

  viz.toggle_api_hints()