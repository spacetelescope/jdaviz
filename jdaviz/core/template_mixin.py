import numpy as np

from functools import cached_property
from ipyvuetify import VuetifyTemplate
from glue.core import HubListener
from glue.core.message import (SubsetDeleteMessage,
                               SubsetUpdateMessage)
from glue.core.subset import RoiSubsetState
from specutils import Spectrum1D
from traitlets import Bool, List, Unicode

from jdaviz import __version__
from jdaviz.core.events import (AddDataMessage, RemoveDataMessage,
                                ViewerAddedMessage, ViewerRemovedMessage)

__all__ = ['TemplateMixin', 'PluginTemplateMixin',
           'BasePluginComponent', 'BaseSelectPluginComponent',
           'SubsetSelect', 'SpatialSubsetSelectMixin', 'SpectralSubsetSelectMixin',
           'ViewerSelect', 'ViewerSelectMixin',
           'DatasetSelect', 'DatasetSelectMixin']


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
    """
    This base class can be inherited by all sidebar plugins to expose common functionality.
    """
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
        self._cached_properties = []
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
        if not len(attrs):
            attrs = self._cached_properties
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


class BaseSelectPluginComponent(BasePluginComponent):
    """
    This base class extends BasePluginComponent for common functionality for a select/dropdown
    component.  The subclasses MUST have an ``items`` traitlet as a list of dictionaries, with
    'label' as the selection entry (and any other optional entries for styling, etc) and a
    ``selected`` string traitlet.  The subclasses should also override ``selected_obj`` and may
    choose to override ``_selected_changed`` (likely with a super call to keep the base logic).
    """
    # default_mode can be one of empty, first, default_text (requires default_text to be set)
    default_mode = 'empty'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._viewer_refs = kwargs.get('viewer_refs', None)
        self._cached_properties = ["selected_obj", "selected_item"]
        default_text = kwargs.get('default_text', None)
        manual_options = kwargs.get('manual_options', [])
        self._default_text = default_text
        if default_text is not None and default_text not in manual_options:
            manual_options = [default_text] + manual_options
        self._manual_options = manual_options

        self.items = [{"label": opt} for opt in manual_options]
        # set default values for traitlets
        if default_text is not None:
            self.selected = default_text

        self.add_observe(kwargs.get('selected'), self._selected_changed)

    @property
    def manual_options(self):
        return self._manual_options
        # read-only access to manual options (cannot change after init)

    @property
    def cached_properties(self):
        return self._cached_properties

    @property
    def viewer_refs(self):
        valid_viewer_refs = [ref for ref in self.app.get_viewer_reference_names()
                             if ref is not None and hasattr(self.app.get_viewer(ref),
                                                            'default_class')]
        if self._viewer_refs is None:
            # exclude dynamically created image viewers (don't have refs) and table viewers
            # that don't contain plottable data
            return valid_viewer_refs
        return [ref for ref in self._viewer_refs if ref in valid_viewer_refs]

    @property
    def viewers(self):
        return [self.app.get_viewer(ref) for ref in self.viewer_refs]

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
        raise NotImplementedError(f"selected_obj not implemented by {self.__class__.__name__}")

    def _apply_default_selection(self):
        if self.selected in self.labels:
            # current selection is valid
            return

        if self.default_mode == 'first':
            self.selected = self.labels[0] if len(self.labels) else ''
        elif self.default_mode == 'default_text':
            self.selected = self._default_text if self._default_text else ''
        else:
            self.selected = ''

    def _selected_changed(self, event):
        self._clear_cache()
        if event['new'] not in self.labels + ['']:
            self._apply_default_selection()
            raise ValueError(f"{event['new']} not one of {self.labels}")


class SubsetSelect(BaseSelectPluginComponent):
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

    * ``selected_min_max(cube)`` (quantity, only applicable for spectral subsets)

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
        :show_if_single_entry="true"
        label="Subset"
        hint="Select subset."
      />

    """
    default_mode = 'default_text'

    def __init__(self, plugin, items, selected, selected_has_subregions=None,
                 viewer_refs=None, default_text=None, manual_options=[], allowed_type=None):
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
        manual_options: list
            list of options to provide that are not automatically populated by subsets.  If
            ``default`` text is provided but not in ``manual_options`` it will still be included as
            the first item in the list.
        allowed_type : str or None
            whether to filter to 'spatial' or 'spectral' types of subsets.  If not provided or None,
            will include both entries.
        """
        super().__init__(plugin,
                         items=items,
                         selected=selected,
                         selected_has_subregions=selected_has_subregions,
                         viewer_refs=viewer_refs,
                         default_text=default_text,
                         manual_options=manual_options)

        if allowed_type not in [None, 'spatial', 'spectral']:
            raise ValueError("allowed_type must be None, 'spatial', or 'spectral'")
        self._allowed_type = allowed_type

        if selected_has_subregions is not None:
            self.selected_has_subregions = False

        self.hub.subscribe(self, SubsetUpdateMessage,
                           handler=lambda msg: self._update_subset(msg.subset, msg.attribute))
        self.hub.subscribe(self, SubsetDeleteMessage,
                           handler=lambda msg: self._delete_subset(msg.subset))

        # intialize any subsets that have already been created
        for lyr in self.app.data_collection.subset_groups:
            self._update_subset(lyr)

    @staticmethod
    def _subset_type(subset):
        if isinstance(subset.subset_state, RoiSubsetState):
            # then this is a spatial subset, we want to ignore
            return 'spatial'
        else:
            return 'spectral'

    def _selected_changed(self, event):
        super()._selected_changed(event)
        self._update_has_subregions()

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

    def _update_has_subregions(self):
        if "selected_has_subregions" in self._plugin_traitlets.keys():
            if self.selected in self._manual_options:
                self.selected_has_subregions = False
            else:
                self.selected_has_subregions = len(self.selected_obj.subregions) > 1

    @cached_property
    def selected_obj(self):
        if self.selected in self.manual_options or self.selected not in self.labels:
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

    def selected_min_max(self, spectrum1d):
        if self.selected_obj is None:
            return np.nanmin(spectrum1d.spectral_axis), np.nanmax(spectrum1d.spectral_axis)
        if self.selected_item.get('type') != 'spectral':
            raise TypeError("This action is only supported on spectral-type subsets")
        else:
            return self.selected_obj.lower, self.selected_obj.upper


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

    * ``spectral_subset.selected_min_max``

    To use in a plugin:

    * add ``SpectralSubsetSelectMixin`` as a mixin to the class
    * use the traitlets and properties above as needed (note the prefix for properties)

    Example template (label and hint are optional)::

      <plugin-subset-select
        :items="spectral_subset_items"
        :selected.sync="spectral_subset_selected"
        :show_if_single_entry="true"
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


class ViewerSelect(BaseSelectPluginComponent):
    """
    Traitlets (in the object, custom traitlets in the plugin):

    * ``items`` (list of dicts with keys: id, reference, ref_or_id)
    * ``selected`` (string)

    Properties (in the object only):

    * ``ids`` (list of ids corresponding to ``items``)
    * ``references`` (list of references corresponding to ``items``)
    * ``labels`` (list of references falling back on ids corresponding to ``items``.  These
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
    default_mode = 'first'

    def __init__(self, plugin, items, selected):
        super().__init__(plugin, items=items, selected=selected)

        self.hub.subscribe(self, ViewerAddedMessage, handler=self._on_viewers_changed)
        self.hub.subscribe(self, ViewerRemovedMessage, handler=self._on_viewers_changed)

        # initialize viewer_items from original viewers
        self._on_viewers_changed()

    @property
    def ids(self):
        return [item['id'] for item in self.items]

    @property
    def references(self):
        return [item['reference'] for item in self.items]

    @cached_property
    def selected_item(self):
        item = super().selected_item
        if item:
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

    @cached_property
    def selected_obj(self):
        return self.app.get_viewer_by_id(self.selected_id)

    def _selected_changed(self, event):
        if event['new'] not in self.labels:
            if self.selected in self.ids:
                # provided id in place of ref
                self.selected = self.labels[self.ids.index(self.selected)]
                return
        return super()._selected_changed(event)

    def _on_viewers_changed(self, msg=None):
        # NOTE: _on_viewers_changed is passed without a msg object during init
        # list of dictionaries with id, ref, ref_or_id
        def _dict_from_viewer(viewer_item):
            d = {'id': viewer_item['id']}
            if viewer_item.get('reference') is not None:
                d['reference'] = viewer_item['reference']
                d['label'] = viewer_item['reference']
            else:
                d['reference'] = None
                d['label'] = viewer_item['id']
            return d

        self.items = [_dict_from_viewer(self.app._viewer_item_by_id(vid))
                      for vid, viewer in self.app._viewer_store.items()
                      if viewer.__class__.__name__ != 'MosvizTableViewer']
        self._apply_default_selection()


class ViewerSelectMixin(VuetifyTemplate, HubListener):
    """
    Applies the ViewerSelect component as a mixin in the base plugin.  This
    automatically adds traitlets as well as new properties to the plugin with minimal
    extra code.  For multiple instances or custom traitlet names/defaults, use the
    ViewerSelect component instead.

    Traitlets (available from the plugin):

    * ``viewer_items``
    * ``viewer_selected``

    Properties (available from the plugin):

    * ``viewer.ids``
    * ``viewer.references``
    * ``viewer.labels``
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


class DatasetSelect(BaseSelectPluginComponent):
    """
    Traitlets (in the object, custom traitlets in the plugin):

    * ``items`` (list of dicts with keys: )
    * ``selected`` (string)

    Properties (in the object only):

    * ``selected_obj``
    * ``selected_dc_item``

    Methods (in the object only):

    * ``get_object``
    * ``add_filter`` (more useful for the mixin, when creating a custom component, pass ``filters``)

    To use in a plugin:

    * create traitlets with default values
    * register with all the automatic logic in the plugin's init by passing the string names
      of the respective traitlets
    * use component in plugin template (see below)
    * refer to properties above based on the interally stored reference to the
      instantiated object of this component

    Example template (label and hint are optional)::

      <plugin-dataset-select
        :items="dataset_items"
        :selected.sync="dataset_selected"
        label="Data"
        hint="Select data."
      />

    """
    default_mode = 'first'

    def __init__(self, plugin, items, selected,
                 filters=['not_from_plugin_model_fitting', 'layer_in_viewer_refs']):
        super().__init__(plugin, items=items, selected=selected)
        self._cached_properties += ["selected_dc_item"]
        self.hub.subscribe(self, AddDataMessage, handler=self._on_data_changed)
        self.hub.subscribe(self, RemoveDataMessage, handler=self._on_data_changed)
        self._filters = filters[:]  # [:] needed to force copy from kwarg default

        # initialize items from original viewers
        self._on_data_changed()

    @property
    def filters(self):
        return self._filters

    def add_filter(self, *filters):
        self._filters += [filter for filter in filters]
        self._on_data_changed()

    @cached_property
    def selected_dc_item(self):
        if self.selected not in self.labels:
            # _apply_default_selection will override shortly anyways
            return None
        return next((x for x in self.app.data_collection if x.label == self.selected))

    def get_object(self, *args, **kwargs):
        if self.selected not in self.labels:
            # _apply_default_selection will override shortly anyways
            return None
        return self.selected_dc_item.get_object(*args, **kwargs)

    @cached_property
    def selected_obj(self):
        if self.selected not in self.labels:
            # _apply_default_selection will override shortly anyways
            return None
        for viewer_ref in self.viewer_refs:
            match = self.app.get_data_from_viewer(viewer_ref, data_label=self.selected)
            if match is not None:
                if hasattr(match, 'get_object'):
                    # cube viewers return the data collection instance from get_data_from_viewer
                    return match.get_object(cls=Spectrum1D)
                return match
        # handle the case of empty Application with no viewer, we'll just pull directly
        # from the data collection
        return self.get_object(cls=Spectrum1D)

    def _is_valid_item(self, data):
        def not_from_plugin(data):
            return data.meta.get('Plugin', None) is None

        def not_from_plugin_model_fitting(data):
            return data.meta.get('Plugin', None) != 'model-fitting'

        def has_metadata(data):
            return hasattr(data, 'meta') and isinstance(data.meta, dict) and len(data.meta)

        def layer_in_viewer_refs(data):
            if not len(self.app.get_viewer_reference_names()):
                # then this is a bar Application object, so ignore this filter
                return True
            for viewer_ref in self.viewer_refs:
                if data.label in [l.layer.label for l in self.app.get_viewer(viewer_ref).layers]: # noqa E741
                    return True
            return False

        def layer_in_spectrum_viewer(data):
            if not len(self.app.get_viewer_reference_names()):
                # then this is a bar Application object, so ignore this filter
                return True
            return data.label in [l.layer.label for l in self.spectrum_viewer.layers] # noqa E741

        def is_image(data):
            return len(data.shape) == 3

        for valid_filter in self.filters:
            if isinstance(valid_filter, str):
                # pull from the functions above, will raise an error if not in locals
                try:
                    valid_filter = locals()[valid_filter]
                except KeyError:
                    raise ValueError(f"{valid_filter} not an implemented filter.")
            if not valid_filter(data):
                return False
        return True

    def _on_data_changed(self, msg=None):
        # NOTE: _on_data_changed is passed without a msg object during init
        # future improvement: don't recreate the entire list when msg is passed
        self.items = [{"label": data.label} for data in self.app.data_collection
                      if self._is_valid_item(data)]
        self._apply_default_selection()
        # future improvement: only clear cache if the selected data entry was changed?
        self._clear_cache(*self._cached_properties)


class DatasetSelectMixin(VuetifyTemplate, HubListener):
    """
    Applies the DatasetSelect component as a mixin in the base plugin.  This
    automatically adds traitlets as well as new properties to the plugin with minimal
    extra code.  For multiple instances or custom traitlet names/defaults, use the
    DatasetSelect component instead.

    Traitlets (available from the plugin):

    * ``dataset_items``
    * ``dataset_selected``

    Properties (available from the plugin):

    * ``dataset.selected_obj``
    * ``dataset.selected_dc_item``

    Methods (available from the plugin):

    * ``dataset.get_object``
    * ``dataset.add_filter`` (preferably used during plugin init)

    To use in a plugin:

    * add ``DatasetSelectMixin`` as a mixin to the class
    * use the traitlets and properties above as needed (note the prefix for properties)

    Example template (label and hint are optional)::

        <v-row>
          <plugin-dataset-select
            :items="dataset_items"
            :selected.sync="dataset_selected"
            label="Data"
            hint="Select data."
          />
        </v-row>
    """
    dataset_items = List().tag(sync=True)
    dataset_selected = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # NOTE: cannot be named self.data or will conflict with existing self.data traitlet!
        self.dataset = DatasetSelect(self, 'dataset_items', 'dataset_selected')
