import numpy as np

from functools import cached_property
from ipyvuetify import VuetifyTemplate
from glue.core import HubListener
from glue.core.message import (SubsetDeleteMessage,
                               SubsetUpdateMessage)
from glue.core.subset import RoiSubsetState
from traitlets import Bool, List, Unicode

from jdaviz import __version__
from jdaviz.core.events import ViewerAddedMessage, ViewerRemovedMessage

__all__ = ['TemplateMixin', 'PluginTemplateMixin',
           'BasePluginComponent',
           'SubsetSelect', 'SpatialSubsetSelectMixin', 'SpectralSubsetSelectMixin',
           'ViewerSelect', 'ViewerSelectMixin']


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


class SubsetSelect(BasePluginComponent):
    """
    Traitlets (in the object, custom traitlets in the plugin):

    * ``items`` (list of dicts with keys: label, color)
    * ``selected`` (string)
    * ``selected_has_subregions`` (bool, OPTIONAL)

    Properties (in the object only):

    * ``labels`` (list of labels corresponding to items)
    * ``selected_item`` (dictionary in ``items`` coresponding to ``selected``, cached)
    * ``selected_obj`` (subset object corresponding to ``selected``, cached)

    Methods (in the object only):

    * ``selected_min(cube)`` (float, only applicable for spectral subsets)
    * ``selected_max(cube)`` (float, only applicable for spectral subsets)

    To use in a plugin:

    * create (empty) traitlets in the plugin
    * register with all the automatic logic in the plugin's init by passing the string names
      of the respective traitlets.  Pass ``allowed_type='spectral'`` or ``allowed_type='spatial'``
      to only support spectral or spatial subsets, respectively.
    * use component in plugin template (see below)
    * refer to properties above based on the interally stored reference to the
      instantiated object of this component
    * observe the traitlets created and defined in the plugin, as necessary

    Example template (label and hint are optional)::

      <plugin-subset-select
        :items="spectral_subset_items"
        :selected.sync="spectral_subset_selected"
        label="Subset"
        hint="Select subset."
      />

    """
    def __init__(self, plugin, items, selected, selected_has_subregions=None,
                 viewer_refs=None, default_text=None, allowed_type=None):
        """
        Parameters
        ----------
        plugin
            the parent plugin object
        items : str
            the name of the items traitlet defined in ``plugin``
        selected : str
            the name of the selected traitlet defined in ``plugin``
        selected_has_subregions: str
            the name of the selected_has_subregions traitlet defined in ``plugin``, optional
        viewer_refs : list
            the reference names of the viewer to extract the subregion.  If not provided or None,
            will loop through all references.
        default_text : str or None
            the text to show for no selection.  If not provided or None, no entry will be provided
            in the dropdown for no selection.
        allowed_type : str or None
            whether to filter to 'spatial' or 'spectral' types of subsets.  If not provided or None,
            will include both entries.
        """
        super().__init__(plugin,
                         items=items,
                         selected=selected,
                         selected_has_subregions=selected_has_subregions)

        self._viewer_refs = viewer_refs
        self._default_text = default_text
        if allowed_type not in [None, 'spatial', 'spectral']:
            raise ValueError("allowed_type must be None, 'spatial', or 'spectral'")
        self._allowed_type = allowed_type

        # set default values for traitlets
        if default_text is not None:
            self.items = [{"label": default_text}]
            self.selected = default_text
        if selected_has_subregions is not None:
            self.selected_has_subregions = False

        self.hub.subscribe(self, SubsetUpdateMessage,
                           handler=lambda msg: self._update_subset(msg.subset, msg.attribute))
        self.hub.subscribe(self, SubsetDeleteMessage,
                           handler=lambda msg: self._delete_subset(msg.subset))
        self.add_observe(selected, self._selected_changed)

        # intialize any subsets that have already been created
        for lyr in self.app.data_collection.subset_groups:
            self._update_subset(lyr)

    @property
    def viewer_refs(self):
        if self._viewer_refs is None:
            return [ref for ref in self.app.get_viewer_reference_names() if ref is not None]
        return self._viewer_refs

    @property
    def viewers(self):
        return [self.app.get_viewer(ref) for ref in self.viewer_refs]

    @staticmethod
    def _subset_type(subset):
        if isinstance(subset.subset_state, RoiSubsetState):
            # then this is a spatial subset, we want to ignore
            return 'spatial'
        else:
            return 'spectral'

    def _apply_default_selection(self):
        # default to the default_text, if available, otherwise empty
        if self._default_text:
            self.selected = self._default_text
        else:
            self.selected = ''

    def _subset_to_dict(self, subset):
        # find layer artist in default spectrum-viewer
        for viewer in self.viewers:
            for layer in viewer.layers:
                if layer.layer.label == subset.label:
                    color = layer.state.color
                    subset_type = self._subset_type(subset)
                    return {"label": subset.label, "color": color, "type": subset_type}
        return {"label": subset.label, "color": False, "type": False}

    def _delete_subset(self, subset):
        # NOTE: calling .remove will not trigger traitlet update
        self.items = [s for s in self.items
                      if s['label'] != subset.label]
        if self.selected not in self.labels:
            self._apply_default_selection()

    def _update_subset(self, subset, attribute=None):
        if self._allowed_type is not None and self._subset_type(subset) != self._allowed_type:
            return

        if subset.label not in self.labels:
            # NOTE: this logic will need to be revisited if generic renaming of subsets is added
            # see https://github.com/spacetelescope/jdaviz/pull/1175#discussion_r829372470
            if subset.label.startswith('Subset'):
                # NOTE: += will not trigger traitlet update
                self.items = self.items + [self._subset_to_dict(subset)]  # noqa
        else:
            if attribute in ('style'):
                # TODO: may need to add label and then rebuild the entire list if/when
                # we add support for renaming subsets

                # NOTE: in-line replacement (self.spectral_subset_items[i] = ...)
                # will not trigger traitlet update
                self.items = [s if s['label'] != subset.label
                              else self._subset_to_dict(subset)
                              for s in self.items]

        if attribute == 'subset_state' and subset.label == self.selected:
            # updated the currently selected subset
            self._clear_cache("selected_obj", "selected_item")
            self._update_has_subregions()

    def _selected_changed(self, event):
        if event['new'] not in self.labels + ['']:
            self._apply_default_selection()
            raise ValueError(f"{event['new']} not one of {self.labels}")
        self._clear_cache("selected_obj", "selected_item")
        self._update_has_subregions()

    def _update_has_subregions(self):
        if "selected_has_subregions" in self._plugin_traitlets.keys():
            if self.selected == self._default_text:
                self.selected_has_subregions = False
            else:
                self.selected_has_subregions = len(self.selected_obj.subregions) > 1

    @property
    def labels(self):
        return [s['label'] for s in self.items if 'label' in s.keys()]

    @cached_property
    def selected_item(self):
        for item in self.items:
            if item['label'] == self.selected:
                return item
        return {}

    @cached_property
    def selected_obj(self):
        if self.selected == self._default_text:
            return None
        subset_type = self.selected_item['type']
        # NOTE: we use reference names here instead of IDs since get_subsets_from_viewer requires
        # that.  For imviz, this will mean we won't be able to loop through each of the viewers,
        # but the original viewer should have access to all the subsets.
        for viewer_ref in self.viewer_refs:
            match = self.app.get_subsets_from_viewer(viewer_ref,
                                                     subset_type=subset_type).get(self.selected)
            if match is not None:
                return match

    def selected_min(self, spectrum1d):
        if self.selected == self._default_text:
            return np.nanmin(spectrum1d.spectral_axis.value)
        if self.selected_item.get('type') != 'spectral':
            raise TypeError("This action is only supported on spectral-type subsets")
        else:
            return self.selected_obj.lower.value

    def selected_max(self, spectrum1d):
        if self.selected == self._default_text:
            return np.nanmax(spectrum1d.spectral_axis.value)
        if self.selected_item.get('type') != 'spectral':
            raise TypeError("This action is only supported on spectral-type subsets")
        else:
            return self.selected_obj.upper.value


class SpectralSubsetSelectMixin(VuetifyTemplate, HubListener):
    """
    Applies the SubsetSelect component with ``allowed_type='spectral'`` as a mixin in the base
    plugin.  This automatically adds traitlets as well as new properties to the plugin with
    minimal extra code.  For multiple instances or custom traitlet names/defaults, use the
    SubsetSelect component instead.

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

      <plugin-subset-select
        :items="spectral_subset_items"
        :selected.sync="spectral_subset_selected"
        label="Spectral region"
        hint="Select spectral region."
      />
    """
    spectral_subset_items = List().tag(sync=True)
    spectral_subset_selected = Unicode().tag(sync=True)
    spectral_subset_selected_has_subregions = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.spectral_subset = SubsetSelect(self,
                                            'spectral_subset_items',
                                            'spectral_subset_selected',
                                            'spectral_subset_selected_has_subregions',
                                            viewer_refs=['spectrum-viewer'],
                                            default_text='Entire Spectrum',
                                            allowed_type='spectral')


class SpatialSubsetSelectMixin(VuetifyTemplate, HubListener):
    """
    Applies the SubsetSelect component with ``allowed_type='spatial'`` as a mixin in the base
    plugin.  This automatically adds traitlets as well as new properties to the plugin with
    minimal extra code.  For multiple instances or custom traitlet names/defaults, use the
    SubsetSelect component instead.

    Traitlets (available from the plugin):

    * ``spatial_subset_items``
    * ``spatial_subset_selected``
    * ``spatial_subset_selected_has_subregions``

    Properties (available from the plugin):

    * ``spatial_subset.labels``
    * ``spatial_subset.selected_obj``

    To use in a plugin:

    * add ``SpatialSubsetSelectMixin`` as a mixin to the class
    * use the traitlets and properties above as needed (note the prefix for properties)

    Example template (label and hint are optional)::

      <plugin-subset-select
        :items="spatial_subset_items"
        :selected.sync="spatial_subset_selected"
        label="Spatial region"
        hint="Select spatial region."
      />
    """
    spatial_subset_items = List().tag(sync=True)
    spatial_subset_selected = Unicode().tag(sync=True)
    spatial_subset_selected_has_subregions = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.spatial_subset = SubsetSelect(self,
                                           'spatial_subset_items',
                                           'spatial_subset_selected',
                                           'spatial_subset_selected_has_subregions',
                                           default_text='No Subset',
                                           allowed_type='spatial')


class ViewerSelect(BasePluginComponent):
    """
    Traitlets (in the object, custom traitlets in the plugin):

    * ``items`` (list of dicts with keys: id, reference, ref_or_id)
    * ``selected`` (string)

    Properties (in the object only):

    * ``ids`` (list of ids corresponding to ``items``)
    * ``references`` (list of references corresponding to ``items``)
    * ``ref_or_ids`` (list of references falling back on ids corresponding to ``items``.  These
        are the values seen in the dropdown, although setting either id or reference to the traitlet
        will still process correctly)
    * ``selected_item`` (dict of the currently selected entry in ``items``)
    * ``selected_id`` (string corresponding to the id of ``selected_item``)
    * ``selected_obj`` (viewer item corresponding to ``selected``)

    To use in a plugin:

    * create traitlets with default values
    * register with all the automatic logic in the plugin's init by passing the string names
      of the respective traitlets
    * use component in plugin template (see below)
    * refer to properties above based on the interally stored reference to the
      instantiated object of this component

    Example template (label and hint are optional)::

      <plugin-viewer-select
        :items="viewer_items"
        :selected.sync="viewer_selected"
        label="Viewer"
        hint="Select viewer."
      />

    """
    def __init__(self, plugin, items, selected):
        super().__init__(plugin, items=items, selected=selected)

        self.hub.subscribe(self, ViewerAddedMessage, handler=self._on_viewers_changed)
        self.hub.subscribe(self, ViewerRemovedMessage, handler=self._on_viewers_changed)
        self.add_observe(selected, self._selected_changed)

        # initialize viewer_items from original viewers
        self._on_viewers_changed()

    @property
    def ids(self):
        return [item['id'] for item in self.items]

    @property
    def references(self):
        return [item['reference'] for item in self.items]

    @property
    def ref_or_ids(self):
        return [item['ref_or_id'] for item in self.items]

    @property
    def selected_item(self):
        for item in self.items:
            if item['ref_or_id'] == self.selected:
                return item
        # try again but this time allow match to id alone.  Note that _selected_changed
        # will handle resetting the trait to the reference since it exists, but this
        # will allow access to the underlying item/object for any observes in the meantime.
        for item in self.items:
            if item['id'] == self.selected:
                return item

    @property
    def selected_id(self):
        return self.selected_item['id']

    @property
    def selected_obj(self):
        return self.app.get_viewer_by_id(self.selected_id)

    def _selected_changed(self, event):
        if event['new'] not in self.ref_or_ids:
            if self.selected in self.ids:
                # provided id in place of ref
                self.selected = self.ref_or_ids[self.ids.index(self.selected)]
            else:
                self._handle_default()
                raise ValueError(f"{event['new']} not one of {self.ref_or_ids}")

    def _handle_default(self):
        if self.selected not in self.ref_or_ids:
            # default to first entry, will trigger any observer on selected
            self.selected = self.ref_or_ids[0] if len(self.items) else ""

    def _on_viewers_changed(self, msg=None):
        # NOTE: _on_viewers_changed is passed without a msg object during init
        # list of dictionaries with id, ref, ref_or_id
        def _dict_from_viewer(viewer_item):
            d = {'id': viewer_item['id']}
            if viewer_item.get('reference') is not None:
                d['reference'] = viewer_item['reference']
                d['ref_or_id'] = viewer_item['reference']
            else:
                d['reference'] = None
                d['ref_or_id'] = viewer_item['id']
            return d

        self.items = [_dict_from_viewer(self.app._viewer_item_by_id(vid))
                      for vid, viewer in self.app._viewer_store.items()
                      if viewer.__class__.__name__ != 'MosvizTableViewer']
        self._handle_default()


class ViewerSelectMixin(VuetifyTemplate, HubListener):
    """
    Applies the ViewerSelect component as a mixin in the base plugin.  This
    automatically adds traitlets as well as new properties to the plugin with minimal
    extra code.  For multiple instances or custom traitlet names/defaults, use the
    SpectralSubsetSelect component instead.

    Traitlets (available from the plugin):

    * ``viewer_items``
    * ``viewer_selected``

    Properties (available from the plugin):

    * ``viewer.ids``
    * ``viewer.references``
    * ``viewer.ref_or_ids``
    * ``viewer.selected_item``
    * ``viewer.selected_id``
    * ``viewer.selected_obj``

    To use in a plugin:

    * add ``ViewerSelectMixin`` as a mixin to the class
    * use the traitlets and properties above as needed (note the prefix for properties)

    Example template (label and hint are optional)::

        <v-row>
          <plugin-viewer-select
            :items="viewer_items"
            :selected.sync="viewer_selected"
            label="Viewer"
            hint="Select viewer."
          />
        </v-row>
    """
    viewer_items = List().tag(sync=True)
    viewer_selected = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.viewer = ViewerSelect(self, 'viewer_items', 'viewer_selected')
