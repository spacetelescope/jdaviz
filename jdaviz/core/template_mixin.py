import numpy as np

from functools import cached_property
from ipyvuetify import VuetifyTemplate
from glue.core import HubListener
from glue.core.message import (SubsetDeleteMessage,
                               SubsetUpdateMessage)
from glue.core.subset import RoiSubsetState
from traitlets import Bool, List, Unicode

from jdaviz import __version__

__all__ = ['TemplateMixin', 'PluginTemplateMixin',
           'BasePluginComponent',
           'SpectralSubsetSelect', 'SpectralSubsetSelectMixin']


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


class PluginTemplateMixin(TemplateMixin):
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


class BasePluginComponent(HubListener):
    """
    This base class handles attaching traitlets from the plugin itself to logic
    handled within the component, support for caching and clearing caches on properties,
    and common properties for accessing the app, etc.
    """
    def __init__(self, plugin, **kwargs):
        self._plugin_traitlets = {k: v for k, v in kwargs.items() if v is not None}
        self._plugin = plugin
        super().__init__()

    def __getattr__(self, attr):
        if attr[0] == '_' or attr not in self._plugin_traitlets.keys():
            return super().__getattribute__(attr)

        return getattr(self._plugin, self._plugin_traitlets.get(attr))

    def __setattr__(self, attr, value, force_super=False):
        if attr[0] == '_' or force_super or attr not in self._plugin_traitlets.keys():
            return super().__setattr__(attr, value)

        return setattr(self._plugin, self._plugin_traitlets.get(attr), value)

    def _clear_cache(self, *attrs):
        """
        provide convenience function to clearing the cache for cached_properties
        """
        for attr in attrs:
            if attr in self.__dict__:
                del self.__dict__[attr]

    def add_observe(self, traitlet_name, handler):
        self._plugin.observe(handler, traitlet_name)

    @property
    def app(self):
        return self._plugin.app

    @property
    def hub(self):
        return self._plugin.hub

    @cached_property
    def spectrum_viewer(self):
        return self._plugin.app.get_viewer("spectrum-viewer")


class SpectralSubsetSelect(BasePluginComponent):
    """
    Traitlets (in the object, custom traitlets in the plugin):

    * ``items`` (list of dicts with keys: label, color)
    * ``selected`` (string)
    * ``selected_has_subregions`` (bool, OPTIONAL)

    Properties (in the object only):

    * ``labels`` (list of labels corresponding to items)
    * ``selected_obj`` (subset object corresponding to selected, cached)

    Methods (in the object only):

    * ``selected_min(cube)`` (float)
    * ``selected_max(cube)`` (float)

    To use in a plugin:

    * create traitlets with default values
    * register with all the automatic logic in the plugin's init by passing the string names
      of the respective traitlets.
    * use component in plugin template (see below)
    * refer to properties above based on the interally stored reference to the
      instantiated object of this component

    Example template (label and hint are optional)::

      <plugin-subset-select
        :items="spectral_subset_items"
        :selected.sync="spectral_subset_selected"
        label="Spectral region"
        hint="Select spectral region."
      />

    """
    def __init__(self, plugin, items, selected, selected_has_subregions=None):
        super().__init__(plugin,
                         items=items,
                         selected=selected,
                         selected_has_subregions=selected_has_subregions)
        self.hub.subscribe(self, SubsetUpdateMessage, handler=self._update_spectral_subset)
        self.hub.subscribe(self, SubsetDeleteMessage, handler=self._delete_spectral_subset)
        self.add_observe(selected, self._selected_changed)

    def _subset_to_dict(self, subset):
        # find layer artist in default spectrum-viewer
        for layer in self.spectrum_viewer.layers:
            if layer.layer.label == subset.label:
                color = layer.state.color
                break
        else:
            color = False
        return {"label": subset.label, "color": color}

    def _delete_spectral_subset(self, msg):
        # NOTE: calling .remove will not trigger traitlet update
        self.items = [s for s in self.items
                      if s['label'] != msg.subset.label]
        if self.selected not in self.labels:
            self.selected = "Entire Spectrum"

    def _update_spectral_subset(self, msg):
        if isinstance(msg.subset.subset_state, RoiSubsetState):
            # then this is a spatial subset, we want to ignore
            return

        if msg.subset.label not in self.labels:
            # NOTE: += will not trigger traitlet update
            self.items = self.items + [self._subset_to_dict(msg.subset)]  # noqa
        else:
            if msg.attribute in ('style'):
                # TODO: may need to add label and then rebuild the entire list if/when
                # we add support for renaming subsets

                # NOTE: in-line replacement (self.spectral_subset_items[i] = ...)
                # will not trigger traitlet update
                self.items = [s if s['label'] != msg.subset.label
                              else self._subset_to_dict(msg.subset)
                              for s in self.items]

        if msg.attribute == 'subset_state' and msg.subset.label == self.selected:
            # updated the currently selected subset
            self._clear_cache("selected_obj")
            self._update_has_subregions()

    def _selected_changed(self, event):
        if event['new'] not in self.labels:
            self.selected = self.labels[0]
            raise ValueError(f"{event['new']} not one of {self.labels}")
        self._clear_cache("selected_obj")
        self._update_has_subregions()

    def _update_has_subregions(self):
        if "selected_has_subregions" in self._plugin_traitlets.keys():
            if self.selected == "Entire Spectrum":
                self.selected_has_subregions = False
            else:
                self.selected_has_subregions = len(self.selected_obj.subregions) > 1

    @property
    def labels(self):
        return [s['label'] for s in self.items if 'label' in s.keys()]

    @cached_property
    def selected_obj(self):
        if self.selected == "Entire Spectrum":
            return None
        return self.app.get_subsets_from_viewer("spectrum-viewer",
                                                subset_type="spectral").get(self.selected)

    def selected_min(self, cube):
        if self.selected == "Entire Spectrum":
            return np.nanmin(cube.spectral_axis.value)
        else:
            return self.selected_obj.lower.value

    def selected_max(self, cube):
        if self.selected == "Entire Spectrum":
            return np.nanmax(cube.spectral_axis.value)
        else:
            return self.selected_obj.upper.value


class SpectralSubsetSelectMixin(VuetifyTemplate, HubListener):
    """
    Applies the SpectralSubsetSelect component as a mixin in the base plugin.  This
    automatically adds traitlets as well as new properties to the plugin with minimal
    extra code.  For multiple instances or custom traitlet names/defaults, use the
    SpectralSubsetSelect component instead.

    Traitlets (available from the plugin):

    * ``spectral_subset_items``
    * ``spectral_subset_selected``
    * ``spectral_subset_selected_has_subregions``

    Properties (available from the plugin):

    * ``spectral_subset.labels``
    * ``spectral_subset.selected_obj``

    Methods (available from the plugin):

    * ``spectral_subset.selected_min``
    * ``spectral_subset.selected_max``

    To use in a plugin:

    * add ``SpectralSubsetSelectMixin`` as a mixin to the class
    * use the traitlets and properties above as needed (note the prefix for properties)

    Example template (label and hint are optional)::

        <v-row>
          <plugin-subset-select
            :items="spectral_subset_items"
            :selected.sync="spectral_subset_selected"
            label="Spectral region"
            hint="Select spectral region."
          />
        </v-row>
    """
    spectral_subset_items = List([{"label": "Entire Spectrum", "color": False}]).tag(sync=True)
    spectral_subset_selected = Unicode("Entire Spectrum").tag(sync=True)
    spectral_subset_selected_has_subregions = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.spectral_subset = SpectralSubsetSelect(self,
                                                    'spectral_subset_items',
                                                    'spectral_subset_selected',
                                                    'spectral_subset_selected_has_subregions')
