import logging
import os

from traitlets import Unicode, List

from ..core.template_mixin import TemplateMixin

__all__ = ['Toolbar']

with open(os.path.join(os.path.dirname(__file__), "toolbar.vue")) as f:
    TEMPLATE = f.read()


class Toolbar(TemplateMixin):
    """
    The main application-level toolbar populated by the input configuration
    file containing references to the registered tools.

    Attributes
    ----------
    template : `Unicode`
        The file containing the vue template for rendering the component.
    tool_names : `List`
        A list containing the string names which will be used to determine
        the rendered tools from the registry.

    Notes
    -----
    The components dictionary for this ~`ipyvuetify.VuetifyTemplate` subclass
    is populated at creation time of the application by querying the related
    registry class. The ``tool_names`` list then determines which items from
    the components dictionary will be rendered.
    """
    template = Unicode(TEMPLATE).tag(sync=True)
    tool_names = List([]).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_tool(self, name):
        """
        Adds a reference to the tool item from the registry that will be
        rendered.

        Parameters
        ----------
        name : str
            The name of the tool plugin.
        """
        logging.info(f"Adding plugin {name} to tray bar.")
        self.tool_names.append(name)

    def register_to_hub(self, hub):
        pass

    def notify(self, message):
        pass
