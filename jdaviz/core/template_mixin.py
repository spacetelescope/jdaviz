from warnings import warn

from ipyvuetify import VuetifyTemplate
from glue.core import HubListener

__all__ = ['TemplateMixin']


class TemplateMixin(VuetifyTemplate, HubListener):
    def __new__(cls, *args, **kwargs):
        """
        Overload object creation so that we can inject a reference to the
        ``Hub`` class before components can be initialized. This makes it so
        hub references on plugins can be passed along to components in the
        call to the initialization method.
        """
        app = kwargs.pop('app', None)
        obj = super().__new__(cls, *args, **kwargs)
        obj._app = app

        return obj

    @property
    def app(self):
        """
        Allows access to the underlying jdaviz application instance. This is
        **not** access to the helper class, but instead the
        `jdaviz.Application` object.
        """
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
