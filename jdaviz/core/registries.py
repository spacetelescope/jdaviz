import re

from glue.config import DictRegistry
from ipyvuetify import VuetifyTemplate
from ipywidgets import Widget


__all__ = ['convert', 'UniqueDictRegistry', 'ViewerRegistry', 'TrayRegistry',
           'ToolRegistry', 'MenuRegistry', 'DataParserRegistry',
           'viewer_registry', 'tray_registry', 'tool_registry', 'menu_registry',
           'data_parser_registry']


def _to_snake(s):
    """Convert dashes in viewer category names to underscores for
    use in class attributes, constructor kwargs, requirement kwargs.
    """
    return s.replace("-", "_")


def convert(name):
    """Converts camel-case strings to snake-case. Used when a user does not define
    a specific name for a registry item.

    Returns
    -------
    val : str
        Name converted to snake-case.
    """
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)

    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


class UniqueDictRegistry(DictRegistry):
    """Base registry class that handles hashmap-like associations between a string
    representation of a plugin and the class to be instantiated.
    """
    def add(self, name, cls):
        """Add an item to the registry.

        Parameters
        ----------
        name : str
            The name referencing the associated class in the registry.
        cls : type
            The class definition (not instance) associated with the name given
            in the first parameter.
        """
        if name in self.members:
            raise ValueError(f"Viewer with the name {name} already exists, "
                             f"please choose a different name.")
        else:
            self.members[name] = cls


class ViewerRegistry(UniqueDictRegistry):
    """Registry containing references to custom viewers."""
    def __call__(self, name=None, label=None):
        def decorator(cls):
            self.add(name, cls, label)
            return cls
        return decorator

    def add(self, name, cls, label=None):
        """Add an item to the registry.

        Parameters
        ----------
        name : str
            The key referencing the associated class in the registry
            dictionary.
        cls : type
            The class definition (not instance) associated with the name given
            in the first parameter.
        label : str, optional
            The label displayed in the tooltip when hovering over the tray tab.
        """
        if name in self.members:
            raise ValueError(f"Viewer with the name {name} already exists, "
                             f"please choose a different name.")
        else:
            self.members[name] = {'label': label, 'cls': cls}


class TrayRegistry(UniqueDictRegistry):
    """Registry containing references to plugins that will be added to the sidebar
    tray tabs.
    """

    default_viewer_category = [
        "spectrum", "table", "image", "spectrum-2d", "flux", "uncert"
    ]
    default_viewer_reqs = {
        category: {
            "cls_attr": f"_default_{_to_snake(category)}_viewer_reference_name",
            "init_kwarg": f"{_to_snake(category)}_viewer_reference_name",
            "require_kwargs": [f"require_{_to_snake(category)}_viewer"]
        } for category in default_viewer_category
    }

    def __call__(self, name=None, label=None, icon=None,
                 viewer_requirements=[]):
        def decorator(cls):
            # The class must inherit from `VuetifyTemplate` in order to be
            # ingestible by the component initialization.
            if not issubclass(cls, VuetifyTemplate):
                raise ValueError(
                    f"Unrecognized superclass for {cls.__name__}. All "
                    f"registered components must inherit from "
                    f"`ipyvuetify.VuetifyTemplate`.")

            self.add(name, cls, label, icon, viewer_requirements)
            return cls
        return decorator

    def add(self, name, cls, label=None, icon=None,
            viewer_requirements=[]):
        """Add an item to the registry.

        Parameters
        ----------
        name : str
            The key referencing the associated class in the registry
            dictionary.
        cls : type
            The class definition (not instance) associated with the name given
            in the first parameter.
        label : str, optional
            The label displayed in the tooltip when hovering over the tray tab.
        icon : str, optional
            The name of the icon to render in the tray tab.
        viewer_requirements : str, list of str
            Required viewers for this plugin.
        """
        if name in self.members:
            raise ValueError(f"Viewer with the name {name} already exists, "
                             f"please choose a different name.")
        else:
            # store the registry name/label so we can access them from the instantiated
            # objects (when determining if a specific plugin is open, for example)
            viewer_reference_name_kwargs = {}

            if not isinstance(viewer_requirements, list):
                viewer_requirements = [viewer_requirements]

            for category in viewer_requirements:
                if category not in self.default_viewer_reqs:
                    raise ValueError(f'Viewer requirements not defined '
                                     f'for viewer category: "{category}" '
                                     f'in plugin "{cls.__class__.__name__}".')

                req = self.default_viewer_reqs[category]
                viewer_cls_attr = req['cls_attr']
                viewer_specific_kwarg = req['init_kwarg']
                requirements = req['require_kwargs']
                viewer_reference_name_kwargs[viewer_cls_attr] = [
                    viewer_specific_kwarg, {
                        k: True for k in requirements
                    }
                ]

            cls._registry_name = name
            cls._registry_label = label
            self.members[name] = {'label': label, 'icon': icon, 'cls': cls,
                                  'viewer_reference_name_kwargs': viewer_reference_name_kwargs}


class ToolRegistry(UniqueDictRegistry):
    """Registry containing references to plugins which will populate the
    application-level toolbar.
    """
    def __call__(self, name=None):
        def decorator(cls):
            # The class must inherit from `Widget` in order to be
            # ingestible by the component initialization.
            if not issubclass(cls, Widget):
                raise ValueError(
                    f"Unrecognized superclass for `{cls.__name__}`. All "
                    f"registered tools must inherit from "
                    f"`ipywidgets.Widget`.")

            self.add(name, cls)
            return cls
        return decorator


class MenuRegistry(UniqueDictRegistry):
    """Registry containing references to plugins that will populate the
    application-level menu bar.
    """
    def __call__(self, name=None):
        def decorator(cls):
            # The class must inherit from `VuetifyTemplate` in order to be
            # ingestible by the component initialization.
            if not issubclass(cls, Widget):
                raise ValueError(
                    f"Unrecognized superclass for {cls.__name__}. All "
                    f"registered tools must inherit from "
                    f"`ipywidgets.Widget`.")

            self.add(name, cls)
            return cls
        return decorator


class DataParserRegistry(UniqueDictRegistry):
    """Registry containing parsing functions for attempting to auto-populate the
    application-defined initial viewers.
    """
    def __call__(self, name=None):
        def decorator(func):
            self.add(name, func)
            return func
        return decorator


viewer_registry = ViewerRegistry()
tray_registry = TrayRegistry()
tool_registry = ToolRegistry()
menu_registry = MenuRegistry()
data_parser_registry = DataParserRegistry()
