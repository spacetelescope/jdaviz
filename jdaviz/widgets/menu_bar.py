import logging
import os

from traitlets import Unicode, List

from ..core.template_mixin import TemplateMixin

__all__ = ['MenuBar']

with open(os.path.join(os.path.dirname(__file__), "menu_bar.vue")) as f:
    TEMPLATE = f.read()


class MenuBar(TemplateMixin):
    """
    The main application-level menu bar populated by the input configuration
    file containing references to the registered tools.

    Attributes
    ----------
    template : `Unicode`
        The file containing the vue template for rendering the component.

    Notes
    -----
    The components dictionary for this ~`ipyvuetify.VuetifyTemplate` subclass
    is populated at creation time of the application by querying the related
    registry class. The ``tool_names`` list then determines which items from
    the components dictionary will be rendered.
    """
    template = Unicode(TEMPLATE).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def register_to_hub(self, hub):
        pass

    def notify(self, message):
        pass
