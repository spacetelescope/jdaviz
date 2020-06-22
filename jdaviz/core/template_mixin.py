import ipyvuetify as v
from glue.core import HubListener
from traitlets import List

__all__ = ['TemplateMixin']


class TemplateMixin(v.VuetifyTemplate, HubListener):
    def __new__(cls, *args, **kwargs):
        """
        Overload object creation so that we can inject a reference to the
        ``Hub`` class before components can be initialized. This makes it so
        hub references on plugins can be passed along to components in the
        call to the initialization method.
        """
        obj = super().__new__(cls, *args, **kwargs)
        obj._app = kwargs.pop('app', None)

        return obj

    @property
    def app(self):
        return self._app

    @property
    def hub(self):
        return self._app.session.hub

    @property
    def session(self):
        return self._app.session

    @property
    def data_collection(self):
        return self._app.session.data_collection
