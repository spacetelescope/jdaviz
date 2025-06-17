import re

from glue.config import DictRegistry
from ipyvuetify import VuetifyTemplate
from ipywidgets import Widget


__all__ = ['convert', 'UniqueDictRegistry', 'ViewerRegistry',
           'ViewerCreatorRegistry', 'TrayRegistry',
           'ToolRegistry', 'MenuRegistry', 'DataParserRegistry',
           'viewer_registry', 'viewer_creator_registry',
           'tray_registry', 'tool_registry', 'menu_registry',
           'data_parser_registry',
           'loader_resolver_registry', 'loader_parser_registry', 'loader_importer_registry']


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
    def add(self, name, cls, overwrite=False):
        """Add an item to the registry.

        Parameters
        ----------
        name : str
            The name referencing the associated class in the registry.
        cls : type
            The class definition (not instance) associated with the name given
            in the first parameter.
        overwrite : bool, optional
            Whether to overwrite an existing entry with the same ``label``.
        """
        if name in self.members and not overwrite:
            raise ValueError(f"Registry item with the name {name} already exists, "
                             f"please choose a different name or pass overwrite=True.")
        else:
            self.members[name] = cls


class ViewerRegistry(UniqueDictRegistry):
    """Registry containing references to custom viewers."""
    def __call__(self, name=None, label=None, overwrite=False):
        def decorator(cls):
            self.add(name, cls, label, overwrite=overwrite)
            return cls
        return decorator

    def add(self, name, cls, label=None, overwrite=False):
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
        overwrite : bool, optional
            Whether to overwrite an existing entry with the same ``label``.
        """
        if name in self.members and not overwrite:
            raise ValueError(f"Viewer with the name {name} already exists, "
                             f"please choose a different name or pass overwrite=True.")
        else:
            self.members[name] = {'label': label, 'cls': cls}


class ViewerCreatorRegistry(UniqueDictRegistry):
    def __call__(self, name=None, overwrite=False):
        def decorator(cls):
            cls._registry_label = name
            self.add(name, cls, overwrite=overwrite)
            return cls
        return decorator


class TrayRegistry(UniqueDictRegistry):
    """Registry containing references to plugins that will be added to the sidebar
    tray tabs.
    """

    default_viewer_category = [
        "spectrum", "table", "image", "spectrum-2d", "flux", "uncert", "profile"
    ]
    default_viewer_reqs = {
        category: {
            "cls_attr": f"_default_{_to_snake(category)}_viewer_reference_name",
            "init_kwarg": f"{_to_snake(category)}_viewer_reference_name",
            "require_kwargs": [f"require_{_to_snake(category)}_viewer"]
        } for category in default_viewer_category
    }

    def __call__(self, name=None, label=None, icon=None,
                 category=None, sidebar=None, subtab=None, overwrite=False):
        def decorator(cls):
            # The class must inherit from `VuetifyTemplate` in order to be
            # ingestible by the component initialization.
            if not issubclass(cls, VuetifyTemplate):
                raise ValueError(
                    f"Unrecognized superclass for {cls.__name__}. All "
                    f"registered components must inherit from "
                    f"`ipyvuetify.VuetifyTemplate`.")

            self.add(name, cls, label, icon, category,
                     sidebar, subtab, overwrite)
            return cls
        return decorator

    def add(self, name, cls, label=None, icon=None,
            category=None, sidebar=None, subtab=None,
            overwrite=False):
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
        overwrite : bool, optional
            Whether to overwrite an existing entry with the same ``label``.
        """
        if name in self.members and not overwrite:
            raise ValueError(f"Tray item with the name {name} already exists, "
                             f"please choose a different name or pass overwrite=True.")
        else:
            cls._registry_name = name
            cls._registry_label = label
            cls._sidebar = sidebar if sidebar is not None else 'plugins'
            cls._subtab = subtab
            self.members[name] = {'label': label, 'name': name,
                                  'icon': icon, 'cls': cls,
                                  'category': category, sidebar: sidebar,
                                  'subtab': subtab}

    def members_in_category(self, category):
        members = [m for m in self.members.values() if m['category'] == category]
        return sorted(members, key=lambda x: x['label'].lower())


class ToolRegistry(UniqueDictRegistry):
    """Registry containing references to plugins which will populate the
    application-level toolbar.
    """
    def __call__(self, name=None, overwrite=False):
        def decorator(cls):
            # The class must inherit from `Widget` in order to be
            # ingestible by the component initialization.
            if not issubclass(cls, Widget):
                raise ValueError(
                    f"Unrecognized superclass for `{cls.__name__}`. All "
                    f"registered tools must inherit from "
                    f"`ipywidgets.Widget`.")

            self.add(name, cls, overwrite)
            return cls
        return decorator


class MenuRegistry(UniqueDictRegistry):
    """Registry containing references to plugins that will populate the
    application-level menu bar.
    """
    def __call__(self, name=None, overwrite=False):
        def decorator(cls):
            # The class must inherit from `VuetifyTemplate` in order to be
            # ingestible by the component initialization.
            if not issubclass(cls, Widget):
                raise ValueError(
                    f"Unrecognized superclass for {cls.__name__}. All "
                    f"registered tools must inherit from "
                    f"`ipywidgets.Widget`.")

            self.add(name, cls, overwrite)
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


class LoaderStepRegistry(UniqueDictRegistry):
    """Registry containing data parsing classes.
    """
    def __init__(self, *args, **kwargs):
        self._step = kwargs.pop('step')
        super().__init__(*args, **kwargs)

    def __call__(self, name=None):
        def decorator(cls):
            cls._registry_label = name
            self.add(name, cls)
            return cls
        return decorator


viewer_registry = ViewerRegistry()
viewer_creator_registry = ViewerCreatorRegistry()
tray_registry = TrayRegistry()
tool_registry = ToolRegistry()
menu_registry = MenuRegistry()
data_parser_registry = DataParserRegistry()  # remove once deconfigging complete
loader_resolver_registry = LoaderStepRegistry(step='resolver')
loader_parser_registry = LoaderStepRegistry(step='parser')
loader_importer_registry = LoaderStepRegistry(step='importer')
