.. _plugin-apis:

*********************
Accessing Plugin APIs
*********************

Each plugin object is wrapped by a public user API which enables interacting with the plugin from
the notebook directly.  The plugin API object for each plugin is accessible through ``viz.plugins``.
For example::

  plugin = viz.plugins['Plot Options']
  plugin.open_in_tray()
  plugin.show('popout')
