import ipyvuetify as v
from glue.core import HubListener


class TemplateMixin(v.VuetifyTemplate, HubListener):
    _shared_state = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__dict__.update(self._shared_state)

    def __new__(cls, *args, **kwargs):
        """
        Overload object creation so that we can inject a reference to the
        ``Hub`` class before components can be initialized. This makes it so
        hub references on plugins can be passed along to components in the
        call to the initialization method.
        """
        hub = kwargs.pop('session', None)
        obj = super().__new__(cls, *args, **kwargs)
        setattr(obj, '_session', hub)

        return obj

    @property
    def hub(self):
        return self.session.hub

    @property
    def session(self):
        return self._session

    @property
    def data_collection(self):
        return self.session.data_collection
