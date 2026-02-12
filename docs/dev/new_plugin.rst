.. _dev-new-plugin:

*************************
Creating a New Plugin
*************************

This guide walks through the process of creating a new plugin for jdaviz, including code structure, documentation, and API reference setup.

Plugin Code Structure
=====================

Directory Layout
----------------

Create a new directory for your plugin under the appropriate config directory:

.. code-block:: text

    jdaviz/configs/<config_name>/plugins/<plugin_name>/
    ├── __init__.py
    ├── <plugin_name>.py
    └── <plugin_name>.vue

For example, for a plugin called "my_analysis" in Imviz:

.. code-block:: text

    jdaviz/configs/imviz/plugins/my_analysis/
    ├── __init__.py
    ├── my_analysis.py
    └── my_analysis.vue

Plugin Class
------------

Create your plugin class in ``<plugin_name>.py``:

.. code-block:: python

    from traitlets import Bool, Unicode
    from jdaviz.core.registries import tray_registry
    from jdaviz.core.template_mixin import PluginTemplateMixin
    from jdaviz.core.user_api import PluginUserApi

    __all__ = ['MyAnalysis']

    @tray_registry('my-analysis', label="My Analysis",
                   category="data:analysis")
    class MyAnalysis(PluginTemplateMixin):
        """
        See the :ref:`My Analysis Plugin Documentation <my-analysis>` for more details.

        Only the following attributes and methods are available through the
        :ref:`public plugin API <plugin-apis>`:

        * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
        * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
        * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.close_in_tray`
        * :meth:`analyze`
        * ``my_parameter``
          Description of the parameter.
        """
        template_file = __file__, "my_analysis.vue"

        my_parameter = Unicode("default").tag(sync=True)

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._plugin_description = 'Brief description for the plugin tray.'

        @property
        def user_api(self):
            return PluginUserApi(self, expose=('my_parameter', 'analyze'))

        def analyze(self):
            """Perform the analysis."""
            # Implementation here
            pass

Key Components
--------------

**@tray_registry decorator**
    Registers the plugin with the tray system:

    - First argument: plugin ID (kebab-case, used in config files)
    - ``label``: Display name shown in the UI
    - ``category``: Determines icon and grouping (e.g., "data:analysis", "data:reduction", "data:manipulation")

**Inheritance**
    Common base classes to inherit from:

    - :class:`~jdaviz.core.template_mixin.PluginTemplateMixin`: Base for all plugins
    - :class:`~jdaviz.core.template_mixin.DatasetSelectMixin`: Adds dataset selection
    - :class:`~jdaviz.core.template_mixin.AddResultsMixin`: Adds result output controls
    - :class:`~jdaviz.core.template_mixin.TableMixin`: Adds table display
    - :class:`~jdaviz.core.template_mixin.PlotMixin`: Adds plot display
    - :class:`~jdaviz.core.template_mixin.ViewerSelectMixin`: Adds viewer selection

**template_file**
    Points to the Vue template file for the UI.

**user_api property**
    Defines what attributes and methods are exposed in the public API. Only items listed in the ``expose`` tuple will be accessible when users interact with the plugin via the helper API.

Class Docstring Format
-----------------------

The docstring must follow this specific format for automatic API reference generation:

1. **First line**: Brief one-line description ending with a reference to the plugin documentation page:

   .. code-block:: python

       """
       See the :ref:`My Analysis Plugin Documentation <my-analysis>` for more details.

2. **API section**: Must start with "Only the following attributes and methods are available through the :ref:`public plugin API <plugin-apis>`:"

3. **API items**: List all exposed items (must match the ``user_api`` expose tuple):

   - Methods use ``:meth:`method_name``` (will be auto-expanded to full path)
   - Attributes/properties use double backticks: ````attribute_name````
   - Include descriptions for attributes

Example:

.. code-block:: python

    """
    See the :ref:`My Analysis Plugin Documentation <my-analysis>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.close_in_tray`
    * :meth:`analyze`
      Perform the main analysis operation.
    * ``dataset`` (:class:`~jdaviz.core.template_mixin.DatasetSelect`)
      Dataset to use for analysis.
    * ``threshold``
      Threshold value for the analysis.
    * ``add_results`` (:class:`~jdaviz.core.template_mixin.AddResults`)
    """

**Important Notes**:

- Do NOT include a self-referential sentence like "See the Plugin Documentation for more details" in the body (the directive will filter it out automatically)
- Use ``:meth:`` only for actual methods (not properties or traits)
- Use double backticks for attributes, properties, and traitlets
- All exposed items must be documented, or you'll get a build warning

Documentation Files
===================

Plugin Documentation Page
--------------------------

Create a new RST file in ``docs/plugins/<plugin_name>.rst``:

.. code-block:: rst

    .. _plugins-my_analysis:

    ***********
    My Analysis
    ***********

    Perform custom analysis on datasets.

    Description
    ===========

    Detailed description of what the plugin does and how to use it.

    Using the Plugin
    ================

    UI Instructions
    ---------------

    1. Open the plugin from the tray
    2. Select your dataset
    3. Configure parameters
    4. Click the analysis button

    API Access
    ==========

    .. code-block:: python

        from jdaviz import Imviz
        imviz = Imviz()
        imviz.load_data('myimage.fits')

        plg = imviz.plugins['My Analysis']
        plg.my_parameter = 'custom_value'
        plg.analyze()

    .. plugin-api-refs::
       :module: jdaviz.configs.imviz.plugins.my_analysis.my_analysis
       :class: MyAnalysis

    See Also
    ========

    * :ref:`plugin-apis` - General plugin API documentation

**Key elements**:

- Label matching the ``@tray_registry`` reference (e.g., ``.. _plugins-my_analysis:``)
- Clear description and usage examples
- ``.. plugin-api-refs::`` directive with correct module path and class name
- The module path should be the full Python import path

Adding to Documentation Index
------------------------------

Add your plugin to the appropriate section in ``docs/configs_index.rst``:

.. code-block:: rst

    .. toctree::
       :maxdepth: 1

       plugins/my_analysis
       plugins/other_plugin

API Reference Setup
===================

Add to API Documentation
-------------------------

Edit ``docs/reference/api_plugins.rst`` to include your plugin module:

.. code-block:: rst

    .. automodapi:: jdaviz.configs.imviz.plugins.my_analysis.my_analysis
       :no-inheritance-diagram:

This generates the full API reference documentation. Place it in the appropriate location alphabetically or by category within the file.

The ``automodapi`` directive will:

- Generate a page with all classes, methods, and functions from the module
- Create cross-references that Sphinx can resolve
- Enable the ``plugin-api-refs`` directive to link to this documentation

Testing Your Plugin
===================

After creating your plugin, verify:

1. **Code loads without errors**:

   .. code-block:: python

       from jdaviz.configs.<config>.plugins.<plugin_name>.<plugin_name> import YourClass

2. **Documentation builds without warnings**:

   .. code-block:: bash

       cd docs
       make clean
       make html

   Check for any Sphinx warnings related to your plugin.

3. **Plugin appears in the tray**:

   Open the appropriate jdaviz configuration and verify your plugin appears in the tray.

4. **API is accessible**:

   .. code-block:: python

       helper = Imviz()  # or other config
       plg = helper.plugins['My Plugin Label']
       # Test exposed attributes/methods

Common Issues
=============

Plugin Not Appearing in Tray
-----------------------------

- Verify ``@tray_registry`` decorator is present and correctly formatted
- Check that the plugin is imported in the config's ``__init__.py``
- Ensure the category matches expected categories

Documentation Build Warnings
-----------------------------

**"WARNING: py:meth reference target not found"**
    - Make sure the plugin is added to ``docs/reference/api_plugins.rst``
    - Verify the module path in ``plugin-api-refs`` directive matches the actual file structure
    - Check that methods referenced with ``:meth:`` are actual methods (not properties)

**"WARNING: The following user API attributes are not documented"**
    - Add all items from ``user_api`` expose tuple to the class docstring
    - Use correct formatting (backticks for attributes, ``:meth:`` for methods)

**"WARNING: undefined label"**
    - Ensure the RST label (e.g., ``.. _plugins-my_analysis:``) is defined
    - Check that referenced labels match exactly (case-sensitive)

Sphinx References Not Resolving
--------------------------------

If you see unresolved references to your plugin class or methods:

1. Confirm ``automodapi`` entry exists in ``api_plugins.rst``
2. Rebuild docs completely: ``make clean && make html``
3. Check the module path in ``plugin-api-refs`` directive uses the full path including duplicate directory/file names if present (e.g., ``my_plugin.my_plugin``)

Examples
========

For complete working examples, refer to existing plugins:

- Simple plugin: :class:`jdaviz.configs.default.plugins.collapse.collapse.Collapse`
- Plugin with table: :class:`jdaviz.configs.imviz.plugins.aper_phot_simple.aper_phot_simple.SimpleAperturePhotometry`
- Plugin with viewer selection: :class:`jdaviz.configs.imviz.plugins.catalogs.catalogs.Catalogs`
- Multi-step plugin: :class:`jdaviz.configs.specviz2d.plugins.spectral_extraction.spectral_extraction.SpectralExtraction2D`
