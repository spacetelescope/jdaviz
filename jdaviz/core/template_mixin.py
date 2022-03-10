from functools import cached_property
from ipyvuetify import VuetifyTemplate
from glue.core import HubListener
from glue.core.message import (SubsetDeleteMessage,
                               SubsetUpdateMessage)
from glue.core.subset import RoiSubsetState
from traitlets import Bool, List, Unicode, observe

from jdaviz import __version__

__all__ = ['TemplateMixin', 'PluginTemplateMixin',
           'BasePluginComponentMixin', 'SpectralSubsetSelectMixin']


class TemplateMixin(VuetifyTemplate, HubListener):
    config = Unicode("").tag(sync=True)
    vdocs = Unicode("").tag(sync=True)

    def __new__(cls, *args, **kwargs):
        """
        Overload object creation so that we can inject a reference to the
        `~glue.core.hub.Hub` class before components can be initialized. This makes it so
        hub references on plugins can be passed along to components in the
        call to the initialization method.
        """
        app = kwargs.pop('app', None)
        obj = super().__new__(cls, *args, **kwargs)
        obj._app = app

        # give the vue templates access to the current config/layout
        obj.config = app.state.settings.get("configuration", "default")

        # give the vue templates access to jdaviz version
        obj.vdocs = 'latest' if 'dev' in __version__ else 'v'+__version__

        # store references to all bqplot widgets that need to handle resizing
        obj.bqplot_figs_resize = []

        return obj

    @property
    def app(self):
        """
        Allows access to the underlying Jdaviz application instance. This is
        **not** access to the helper class, but instead the
        `jdaviz.app.Application` object.
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


class MultipleHandlerMixin(VuetifyTemplate, HubListener):
    """
    This mixin adds support for multiple handlers for the same message from a class,
    and should replace:

    self.hub.subscribe(self, MessageClass, handler=self._handler)

    with

    self.add_handler(MessageClass, self._handler)
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._wrapped_handlers = {}

    def _call_handlers(self, message_cls, msg):
        for handler in self._wrapped_handlers.get(message_cls.__name__, []):
            if isinstance(handler, str):
                getattr(self, handler)(msg)
            else:
                handler(msg)

    def add_handler(self, message_cls, handler):
        if message_cls.__name__ not in self._wrapped_handlers.keys():
            self.hub.subscribe(self, message_cls,
                               handler=lambda msg: self._call_handlers(message_cls, msg))
            self._wrapped_handlers[message_cls.__name__] = []

        self._wrapped_handlers[message_cls.__name__] += [handler]


class PluginTemplateMixin(TemplateMixin, MultipleHandlerMixin):
    disabled_msg = Unicode("").tag(sync=True)
    plugin_opened = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app.state.add_callback('tray_items_open', self._mxn_update_plugin_opened)
        self.app.state.add_callback('drawer', self._mxn_update_plugin_opened)

    def _mxn_update_plugin_opened(self, new_value):
        app_state = self.app.state
        tray_names_open = [app_state.tray_items[i]['name'] for i in app_state.tray_items_open]
        self.plugin_opened = app_state.drawer and self._registry_name in tray_names_open


class BasePluginComponentMixin(MultipleHandlerMixin):
    def _clear_cache(self, *attrs):
        """
        provide convenience function to clearing the cache for cached_properties
        """
        for attr in attrs:
            if attr in self.__dict__:
                del self.__dict__[attr]

    @cached_property
    def spectrum_viewer(self):
        return self.app.get_viewer("spectrum-viewer")


class SpectralSubsetSelectMixin(BasePluginComponentMixin):
    """
    Traitlets:

    * spectral_subset_items (list of dicts with keys: label, color)
    * selected_subset (string)

    Properties:

    * spectral_subset_labels (list of labels corresponding to spectral_subset_items)
    * selected_subset_obj (subset object corresponding to selected_subset, cached)

    Example template (label and hint are optional):
    <v-row>
      <mxn-subset-select
        :spectral_subset_items="spectral_subset_items"
        :selected_subset.sync="selected_subset"
        label="Spectral region"
        hint="Select spectral region."
      />
    </v-row>
    """
    spectral_subset_items = List([{"label": "Entire Spectrum", "color": False}]).tag(sync=True)
    selected_subset = Unicode("Entire Spectrum").tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # we'll use SubsetUpdateMessage to both make updates to existing subsets
        # and to catch new subsets (SubsetCreateMessage does not yet contain
        # the fully-resolved subset, so we can't yet tell if its spectral or spatial)
        self.add_handler(SubsetUpdateMessage, self._mxn_update_spectral_subset)
        self.add_handler(SubsetDeleteMessage, self._mxn_delete_spectral_subset)

    def _mxn_subset_to_dict(self, subset):
        # find layer artist in default spectrum-viewer
        for layer in self.app.get_viewer("spectrum-viewer").layers:
            if layer.layer.label == subset.label:
                color = layer.state.color
                break
        else:
            color = False
        return {"label": subset.label, "color": color}

    def _mxn_delete_spectral_subset(self, msg):
        # NOTE: calling .remove will not trigger traitlet update
        self.spectral_subset_items = [s for s in self.spectral_subset_items
                                      if s['label'] != msg.subset.label]
        if self.selected_subset not in self.spectral_subset_labels:
            self.selected_subset = "Entire Spectrum"

    def _mxn_update_spectral_subset(self, msg):
        if isinstance(msg.subset.subset_state, RoiSubsetState):
            # then this is a spatial subset, we want to ignore
            return

        if msg.subset.label not in self.spectral_subset_labels:
            # NOTE: += will not trigger traitlet update
            self.spectral_subset_items = self.spectral_subset_items + [self._mxn_subset_to_dict(msg.subset)]  # noqa
        else:
            if msg.attribute not in ('style'):
                # TODO: may need to add label and then rebuild the entire list if/when
                # we add support for renaming subsets
                return
            # NOTE: in-line replacement (self.spectral_subset_items[i] = ...)
            # will not trigger traitlet update
            self.spectral_subset_items = [s if s['label'] != msg.subset.label
                                          else self._mxn_subset_to_dict(msg.subset)
                                          for s in self.spectral_subset_items]

    @observe("selected_subset")
    def _mxn_selected_subset_changed(self, event):
        self._clear_cache("selected_subset_obj")

    @property
    def spectral_subset_labels(self):
        return [s['label'] for s in self.spectral_subset_items]

    @cached_property
    def selected_subset_obj(self):
        if self.selected_subset == "Entire Spectrum":
            return None
        return self.app.get_subsets_from_viewer("spectrum-viewer",
                                                subset_type="spectral").get(self.selected_subset)
