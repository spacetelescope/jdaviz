*****************
Plugin Components
*****************

Plugin components exist to provide re-usable UI elements across multiple plugins, both for 
consistency in behavior between plugins and also for simplification of code.

The general concept is to move as much shared code into these components, and out of the plugins, as
possible.

Design Philosophy
-----------------

Each component consists of three parts: 

1. Python component class in ``template_mixin.py`` which inherits from ``BasePluginComponent`` and
passes the string names of the traitlets it needs to ``__init__`` as kwargs.  This class isolates the
logic from the plugin itself, while still providing convenient access to the traitlets which are
defined in the plugin itself (and in doing so, allows using those same traitlets within the plugin
in the same way as any other traitlet in the plugin). Within this class, it is necessary to use
``self.add_observe`` instead of the ``@observe`` decorator for all traitlets, so that the callback
can reference the traitlet in the plugin properly. 

2. Python mixin class in ``template_mixin.py`` which inherits from ``VuetifyTemplate`` and
``HubListener``. This class defines default traitlets as well as the attribute for the component
object itself for plugins to make use of the accompanying component.  In some cases, the component
class will be used manually with custom traitlets (especially if/when using multiple instances of
the same component within a single plugin). 

3. ``.vue`` template file in ``jdaviz/components``, which are registered in ``app.py``.  These
templates are not linked directly to the python class, but rather should pass all necessary
traitlets and options when called from within the template file for the plugin itself. Note that
this means that the instance of the component cannot be rendered individually, but also allows for
components to interact with each other easily through traitlet events within the plugin. If nesting
these inside each other, it might be necessary to manually re-emit events higher up the tree with
something like ``@update:value="$emit('update_value', $event)"``.


``BasePluginComponent`` provides the following functionality to all components:

* ``app``, ``hub``, and ``plugin`` properties to access the respective instances.
* ``viewer_dicts`` property to access a list of dictionaries, with keys: ``viewer``, ``id``, 
  ``reference``, and ``label`` (``reference`` if available, otherwise ``id``).
* ``add_observe`` function to connect a callback to the proper traitlet in the parent plugin.  This
  can optionally take ``first=True`` to ensure the callback will be processed before any
  ``@observe`` watchers in the plugin.
* overrides ``getattr`` and ``setattr`` to redirect any calls to the internal traitlet attributes
  to those in the plugin.

Considerations
--------------

* Each class can only subscribe to each ``Message`` object once (via ``self.hub.subscribe``),
  without introducing extra wrappers.  By isolating the component-logic from the plugin, the
  component and the plugin itself can subscribe to the same message without issues.
* Having the whole component in a Mixin would also prevent the ability to have multiple instances
  of the same component within a single plugin.  This is needed in several places: subsets in line
  analysis and aperture photometry, for example.
* Having each component class be standalone with its own linked template (so that it can be rendered
  individually) would complicate communication between components.  The component would need its own
  traitlets which are then synced to traitlets in the plugin and/or message events would need to be
  used.
* Plugin components are specifically designed to be used within plugins, and should not be used
  elsewhere.
