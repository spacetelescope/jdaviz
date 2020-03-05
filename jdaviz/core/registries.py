from glue.config import DictRegistry
import re
from functools import wraps
from ipyvuetify import VuetifyTemplate
from ipywidgets import Widget


__all__ = ['viewer_registry', 'tray_registry', 'tool_registry', 'ViewerRegistry', 'TrayRegistry',
           'ToolRegistry', 'MenuRegistry']


def convert(name):
    """
    Converts camel case strings to snake case. Used when a user does not define
    a specific name for a registry item.

    Returns
    -------
    str
        Name converted to snake case.
    """
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)

    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


class UniqueDictRegistry(DictRegistry):
    """
    Base registry class that handles hashmap-like associations between a string
    representation of a plugin and the class to be instantiated.
    """
    def add(self, name, cls):
        """
        Add an item to the registry.

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
    """
    Registry containing references to custom viewers.
    """
    def __call__(self, name=None, label=None):
        def decorator(cls):
            self.add(name, cls, label)
        return decorator

    def add(self, name, cls, label=None):
        """
        Add an item to the registry.

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
    """
    Registry containing references to plugins that will be added to the sidebar
    tray tabs.
    """
    def __call__(self, name=None, label=None, icon=None):
        def decorator(cls):
            # The class must inherit from `VuetifyTemplate` in order to be
            # ingestible by the component initialization.
            if not issubclass(cls, VuetifyTemplate):
                raise ValueError(
                    f"Unrecognized superclass for {cls.__name__}. All "
                    f"registered components must inherit from "
                    f"`ipyvuetify.VuetifyTemplate`.")

            self.add(name, cls, label, icon)
        return decorator

    def add(self, name, cls, label=None, icon=None):
        """
        Add an item to the registry.

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
        """
        if name in self.members:
            raise ValueError(f"Viewer with the name {name} already exists, "
                             f"please choose a different name.")
        else:
            self.members[name] = {'label': label, 'icon': icon, 'cls': cls}


class ToolRegistry(UniqueDictRegistry):
    """
    Registry containing references to plugins which will populate the
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
        return decorator


class MenuRegistry(UniqueDictRegistry):
    """
    Registry containg referenecs to plugins that will populate the application-
    level menu bar.
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
        return decorator


viewer_registry = ViewerRegistry()
tray_registry = TrayRegistry()
tool_registry = ToolRegistry()
menu_registry = MenuRegistry()
