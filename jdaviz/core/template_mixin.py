import numpy as np

from functools import cached_property
from ipyvuetify import VuetifyTemplate
from glue.config import colormaps
from glue.core import HubListener
from glue.core.message import (DataCollectionAddMessage,
                               DataCollectionDeleteMessage,
                               SubsetCreateMessage,
                               SubsetDeleteMessage,
                               SubsetUpdateMessage)
from glue.core.subset import RoiSubsetState
from glue_jupyter.bqplot.image import BqplotImageView
from glue_jupyter.widgets.linked_dropdown import get_choices as _get_glue_choices
from specutils import Spectrum1D
from traitlets import Any, Bool, HasTraits, List, Unicode, observe

from ipywidgets import widget_serialization
from ipypopout import PopoutButton

from jdaviz import __version__
from jdaviz.core.events import (AddDataMessage, RemoveDataMessage,
                                ViewerAddedMessage, ViewerRemovedMessage)


__all__ = ['TemplateMixin', 'PluginTemplateMixin',
           'BasePluginComponent', 'BaseSelectPluginComponent',
           'SubsetSelect', 'SpatialSubsetSelectMixin', 'SpectralSubsetSelectMixin',
           'ViewerSelect', 'ViewerSelectMixin',
           'DatasetSelect', 'DatasetSelectMixin',
           'AutoLabel', 'AutoLabelMixin',
           'AddResults', 'AddResultsMixin']


class TemplateMixin(VuetifyTemplate, HubListener):
    config = Unicode("").tag(sync=True)
    vdocs = Unicode("").tag(sync=True)
    popout_button = Any().tag(sync=True, **widget_serialization)

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.popout_button = PopoutButton(self, window_features='popup,width=400,height=600')

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

    def add_observe(self, traitlet_name, handler, first=False):
        self._plugin.observe(handler, traitlet_name)
        if first:
            # re-order the callbacks so this one is first
            existing_callbacks = self._plugin._trait_notifiers[traitlet_name]['change']
            new_order = [handler] + [other for other in existing_callbacks if other != handler]
            self._plugin._trait_notifiers[traitlet_name]['change'] = new_order

    @property
    def plugin(self):
        """
        Access the parent plugin object
        """
        return self._plugin

    @property
    def app(self):
        """
        Access the parent app object
        """
        return self._plugin.app

    @property
    def hub(self):
        """
        Access the hub attached to the parent plugin object
        """
        return self._plugin.hub

    @property
    def viewer_dicts(self):
        def _dict_from_viewer(viewer, viewer_item, index=None):
            d = {'viewer': viewer, 'id': viewer_item['id']}
            if viewer_item.get('reference') is not None:
                d['reference'] = viewer_item['reference']
                d['label'] = viewer_item['reference']
            else:
                d['reference'] = None
                d['label'] = viewer_item['id']
            if index is not None:
                d['icon'] = f"mdi-numeric-{index+1}-circle-outline"
            return d

        return [_dict_from_viewer(viewer, self.app._viewer_item_by_id(vid), index)
                for index, (vid, viewer) in enumerate(self.app._viewer_store.items())
                if viewer.__class__.__name__ != 'MosvizTableViewer']

    @cached_property
    def spectrum_viewer(self):
        return self._plugin.app.get_viewer("spectrum-viewer")


class BaseSelectPluginComponent(BasePluginComponent, HasTraits):
    """
    This base class extends BasePluginComponent for common functionality for a select/dropdown
    component.  The subclasses MUST have an ``items`` traitlet as a list of dictionaries, with
    'label' as the selection entry (and any other optional entries for styling, etc) and a
    ``selected`` string traitlet.  The subclasses should also override ``selected_obj`` and may
    choose to override ``_selected_changed`` (likely with a super call to keep the base logic).
    """
    filters = List([]).tag(sync=True)

    def __init__(self, *args, **kwargs):
        # default_mode can be one of empty, first, default_text (requires default_text to be set)
        default_mode = kwargs.pop('default_mode', 'empty')
        default_text = kwargs.pop('default_text', None)
        manual_options = kwargs.pop('manual_options', [])
        self._viewers = kwargs.pop('viewers', None)
        # we'll pop from kwargs now to avoid passing to the super.__init__, but need to
        # wait for everything else to be set before setting to the traitlet
        filters = kwargs.pop('filters', [])[:]  # [:] needed to force copy from kwarg default

        super().__init__(*args, **kwargs)
        self._cached_properties = ["selected_obj", "selected_item"]

        self._default_mode = default_mode
        self._default_text = default_text
        if default_text is not None and default_text not in manual_options:
            manual_options = [default_text] + manual_options
        self._manual_options = manual_options

        self.items = [{"label": opt} for opt in manual_options]
        # set default values for traitlets
        if default_text is not None:
            self.selected = default_text

        if kwargs.get('multiselect'):
            self.add_observe(kwargs.get('multiselect'), self._multiselect_changed)

        # this callback MUST come first so that any plugins that use @observe have those
        # callbacks triggered AFTER the cache is cleared and the value is checked against
        # valid options
        self.add_observe(kwargs.get('selected'), self._selected_changed, first=True)
        self.filters = filters

    @property
    def is_multiselect(self):
        if not hasattr(self, 'multiselect'):
            return False
        else:
            return self.multiselect

    @property
    def default_text(self):
        return self._default_text

    @property
    def manual_options(self):
        return self._manual_options
        # read-only access to manual options (cannot change after init)

    @property
    def cached_properties(self):
        return self._cached_properties

    def add_filter(self, *filters):
        self.filters += [filter for filter in filters]

    @property
    def viewer_dicts(self):
        all_viewer_dicts = super().viewer_dicts
        if self._viewers is None:
            return all_viewer_dicts
        # filter to those provided (either by id or reference)
        return [v for v in all_viewer_dicts
                if v['reference'] in self._viewers or v['id'] in self._viewers]

    @property
    def viewer_refs(self):
        return [v['reference'] for v in self.viewer_dicts]

    @property
    def viewer_ids(self):
        return [v['id'] for v in self.viewer_dicts]

    @property
    def viewers(self):
        return [v['viewer'] for v in self.viewer_dicts]

    @property
    def labels(self):
        return [s['label'] for s in self.items if 'label' in s.keys()]

    def _get_selected_item(self, selected):
        for item in self.items:
            if item['label'] == selected:
                return item
        return {}

    @cached_property
    def selected_item(self):
        if self.is_multiselect:
            items = [self._get_selected_item(selected) for selected in self.selected]
            if not len(items):
                return {}
            return {k: [item[k] for item in items] for k in items[0].keys()}
        return self._get_selected_item(self.selected)

    @cached_property
    def selected_obj(self):
        raise NotImplementedError(f"selected_obj not implemented by {self.__class__.__name__}")

    @property
    def default_mode(self):
        return self._default_mode

    def _apply_default_selection(self):
        # TODO: make this multi-ready
        is_valid = self.selected in self.labels
        if callable(self.default_mode):
            # callable was defined and passed by the plugin or inheriting component.
            # the callable takes the viewer component as input as well as the `is_valid` boolean
            # which states if the current selection is already valid and returns the default label
            # (to keep the current selection
            self.selected = self.default_mode(self, is_valid=is_valid)
            return

        if is_valid:
            # current selection is valid
            return

        if self.default_mode == 'first':
            self.selected = self.labels[0] if len(self.labels) else ''
        elif self.default_mode == 'default_text':
            self.selected = self._default_text if self._default_text else ''
        else:
            self.selected = ''

    def _is_valid_item(self, item, filter_callables={}):
        for valid_filter in self.filters:
            if isinstance(valid_filter, str):
                # pull from the functions above (should be subclassed),
                # will raise an error if not in locals
                try:
                    valid_filter = filter_callables[valid_filter]
                except KeyError:
                    raise ValueError(f"{valid_filter} not an implemented filter.")
            if not valid_filter(item):
                return False
        return True

    def _multiselect_changed(self, event):
        self._clear_cache()
        if self.is_multiselect:
            self.selected = [self.selected]
        elif isinstance(self.selected, list):
            self.selected = self.selected[0]
        else:
            self._apply_default_selection()

    def _selected_changed(self, event):
        self._clear_cache()
        if self.is_multiselect:
            if not isinstance(event['new'], list):
                self.selected = [event['new']]
                return
            if not np.all([item in self.labels + [''] for item in event['new']]):
                self._apply_default_selection()
                raise ValueError(f"not all items in {event['new']} are one of {self.labels}")
        else:
            if event['new'] not in self.labels + ['']:
                self._apply_default_selection()
                raise ValueError(f"{event['new']} not one of {self.labels}")


class LayerSelect(BaseSelectPluginComponent):
    """
    Traitlets (in the object, custom traitlets in the plugin):

    * ``items`` (list of dicts with keys: label, color)
    * ``selected`` (string)

    Properties (in the object only):

    * ``labels`` (list of labels corresponding to items)
    * ``selected_item`` (dictionary in ``items`` coresponding to ``selected``, cached)
    * ``selected_obj`` (layer object corresponding to ``selected``, cached)


    To use in a plugin:

    * create (empty) traitlets in the plugin
    * register with all the automatic logic in the plugin's init by passing the string names
      of the respective traitlets.
    * use component in plugin template (see below)
    * refer to properties above based on the interally stored reference to the
      instantiated object of this component
    * observe the traitlets created and defined in the plugin, as necessary

    Example template (label and hint are optional)::

      <plugin-layer-select
        :items="layer_items"
        :selected.sync="layer_selected"
        :show_if_single_entry="true"
        label="Layer"
        hint="Select layer."
      />

    """
    def __init__(self, plugin, items, selected, viewer,
                 multiselect=None,
                 default_text=None, manual_options=[], allowed_type=None,
                 default_mode='first'):
        """
        Parameters
        ----------
        plugin
            the parent plugin object
        items : str
            the name of the items traitlet defined in ``plugin``
        selected : str
            the name of the selected traitlet defined in ``plugin``
        viewer: str
            the name of the traitlet defined in ``plugin`` storing the viewer(s) to expose the
            layers
        default_text : str or None
            the text to show for no selection.  If not provided or None, no entry will be provided
            in the dropdown for no selection.
        manual_options: list
            list of options to provide that are not automatically populated by subsets.  If
            ``default`` text is provided but not in ``manual_options`` it will still be included as
            the first item in the list.
        """
        super().__init__(plugin,
                         items=items,
                         selected=selected,
                         viewer=viewer,
                         multiselect=multiselect,
                         default_text=default_text,
                         manual_options=manual_options,
                         default_mode=default_mode)

        self.hub.subscribe(self, AddDataMessage,
                           handler=lambda _: self._on_layers_changed())
        self.hub.subscribe(self, RemoveDataMessage,
                           handler=lambda _: self._on_layers_changed())
        self.hub.subscribe(self, SubsetCreateMessage,
                           handler=lambda _: self._on_layers_changed())
        # will need SubsetUpdateMessage for name only (style shouldn't force a full refresh)
        # self.hub.subscribe(self, SubsetUpdateMessage,
        #                    handler=lambda _: self._on_layers_changed())
        self.hub.subscribe(self, SubsetDeleteMessage,
                           handler=lambda _: self._on_layers_changed())

        self.add_observe(viewer, self._on_viewer_changed)
        self._on_layers_changed()

    def _get_viewer(self, viewer):
        # newer will likely be the viewer name in most cases, but viewer id in the case
        # of additional viewers in imviz.
        try:
            return self.app.get_viewer(viewer)
        except TypeError:
            return self.app.get_viewer_by_id(viewer)

    def _layer_to_dict(self, layer, index=None):
        d = {"label": layer.layer.label, "color": layer.state.color}
        if index is not None:
            d['icon'] = f"mdi-alpha-{chr(97 + index)}-box-outline"
        return d

    def _on_viewer_changed(self, msg=None):
        # we don't want to update the layers if we're just toggling between single and multi-select
        old, new = msg['old'], msg['new']
        if not isinstance(old, list):
            old = [old]
        if not isinstance(new, list):
            new = [new]
        if new != old:
            self._clear_cache()
            self._on_layers_changed()

    def _valid_layer(self, viewer, layer):
        if isinstance(viewer, BqplotImageView) and self.plugin.config == 'cubeviz':
            # exclude spectral subsets in image viewers (but not in 2d spectrum viewers)
            if hasattr(layer.state.layer, 'subset_state') and not isinstance(layer.state.layer.subset_state, RoiSubsetState):  # noqa
                return False
        return True

    @observe('filters')
    def _on_layers_changed(self, msg=None):
        # NOTE: _on_layers_changed is passed without a msg object during init

        viewer_names = self.viewer
        if not isinstance(viewer_names, list):
            viewer_names = [viewer_names]
        viewers = [self._get_viewer(viewer) for viewer in viewer_names]

        manual_items = [{'label': label} for label in self.manual_options]
        layers = [layer for viewer in viewers for layer in viewer.layers if self._valid_layer(viewer, layer)]  # noqa
        # remove duplicates - NOTE: by doing this, any color-mismatch between layers with the
        # same name in different viewers will be randomly assigned within plot_options
        # based on which was found _first.
        layer_labels = [layer.layer.label for layer in layers]
        _, inds = np.unique(layer_labels, return_index=True)
        layers = [layers[i] for i in inds]

        self.items = manual_items + [self._layer_to_dict(layer, index) for index, layer in enumerate(layers)]  # noqa
        self._apply_default_selection()

    @cached_property
    def selected_obj(self):
        viewer_names = self.viewer
        if not isinstance(viewer_names, list):
            # case for single-select on the viewer select
            viewer_names = [viewer_names]

        selected = self.selected
        if not isinstance(selected, list):
            selected = [selected]

        viewers = [self._get_viewer(viewer_name) for viewer_name in viewer_names]

        layers = [[layer for layer in viewer.layers
                   if layer.layer.label in selected and self._valid_layer(viewer, layer)]
                  for viewer in viewers]

        if not self.multiselect and len(layers) == 1:
            return layers[0]
        else:
            return layers


class LayerSelectMixin(VuetifyTemplate, HubListener):
    """
    Applies the LayerSelect component as a mixin in the base plugin.  This
    automatically adds traitlets as well as new properties to the plugin with minimal
    extra code.  For multiple instances or custom traitlet names/defaults, use the
    component instead.

    To use in a plugin:

    * add ``LayerSelectMixin`` as a mixin to the class
    * use the traitlets available from the plugin or properties/methods available from
      ``plugin.layer``.

    Example template (label and hint are optional)::

      <plugin-layer-select
        :items="layer_items"
        :selected.sync="layer_selected"
        :show_if_single_entry="true"
        label="Layer"
        hint="Select layer."
      />

    """
    layer_items = List().tag(sync=True)
    layer_selected = Any().tag(sync=True)
    layer_viewer = Unicode().tag(sync=True)
    layer_multiselect = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layer = LayerSelect(self,
                                 'layer_items',
                                 'layer_selected',
                                 'layer_viewer',
                                 'layer_multiselect')


class SubsetSelect(BaseSelectPluginComponent):
    """
    Traitlets (in the object, custom traitlets in the plugin):

    * ``items`` (list of dicts with keys: label, color, type)
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
    def __init__(self, plugin, items, selected, selected_has_subregions=None,
                 viewers=None, default_text=None, manual_options=[], allowed_type=None,
                 default_mode='default_text'):
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
        viewers : list
            the reference names or ids of the viewer to extract the subregion.  If not provided o
            None, will loop through all references.
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
                         viewers=viewers,
                         default_text=default_text,
                         manual_options=manual_options,
                         default_mode=default_mode)

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
            # 'type' can be passed manually rather than coming from SubsetUpdateMessage.attribute
            if attribute in ('style', 'type'):
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
    Applies the SubsetSelect component as a mixin in the base plugin.  This
    automatically adds traitlets as well as new properties to the plugin with minimal
    extra code.  For multiple instances or custom traitlet names/defaults, use the
    component instead.

    To use in a plugin:

    * add ``SpectralSubsetSelectMixin`` as a mixin to the class
    * use the traitlets available from the plugin or properties/methods available from
      ``plugin.spectral_subset``.

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
                                            viewers=['spectrum-viewer'],
                                            default_text='Entire Spectrum',
                                            allowed_type='spectral')


class SpatialSubsetSelectMixin(VuetifyTemplate, HubListener):
    """
    Applies the SubsetSelect component as a mixin in the base plugin.  This
    automatically adds traitlets as well as new properties to the plugin with minimal
    extra code.  For multiple instances or custom traitlet names/defaults, use the
    component instead.

    To use in a plugin:

    * add ``SpatialSubsetSelectMixin`` as a mixin to the class
    * use the traitlets available from the plugin or properties/methods available from
      ``plugin.spatial_subset``.

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

    * ``items`` (list of dicts with keys: id, reference, label)
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
    def __init__(self, plugin, items, selected,
                 multiselect=None,
                 default_text=None, manual_options=[], default_mode='first'):
        super().__init__(plugin, items=items, selected=selected,
                         multiselect=multiselect,
                         default_text=default_text, manual_options=manual_options,
                         default_mode=default_mode)

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

    def _get_selected_item(self, selected):
        if selected in self.manual_options:
            return {}
        item = super()._get_selected_item(selected)
        if item:
            return item

        # try again but this time allow match to id alone.  Note that _selected_changed
        # will handle resetting the trait to the reference since it exists, but this
        # will allow access to the underlying item/object for any observes in the meantime.
        for item in self.items:
            if item['id'] == selected:
                return item

    @property
    def selected_id(self):
        return self.selected_item.get('id', None)

    @property
    def selected_reference(self):
        return self.selected_item.get('reference', None)

    def _get_selected_obj(self, selected, selected_id):
        if selected in self.manual_options or selected_id is None:
            return None
        return self.app.get_viewer_by_id(selected_id)

    @cached_property
    def selected_obj(self):
        if self.is_multiselect and len(self.selected):
            return [self._get_selected_obj(selected, selected_id)
                    for selected, selected_id in zip(self.selected, self.selected_id)]
        return self._get_selected_obj(self.selected, self.selected_id)

    def _selected_changed(self, event):
        self._clear_cache()
        if self.is_multiselect and isinstance(event['new'], list):
            new_selected = []
            for entry in event['new']:
                if entry in self.labels + self.manual_options:
                    new_selected.append(entry)
                elif entry in self.ids:
                    new_selected.append(self.labels[self.ids.index(entry)])
                else:
                    raise ValueError(f"could not map {entry} to valid choice")
            self.selected = new_selected
            return
        else:
            if event['new'] not in self.labels + self.manual_options:
                if self.selected in self.ids:
                    # provided id in place of ref
                    self.selected = self.labels[self.ids.index(self.selected)]
                    return
        return super()._selected_changed(event)

    def _is_valid_item(self, viewer):
        def is_spectrum_viewer(viewer):
            return 'ProfileView' in viewer.__class__.__name__

        def is_image_viewer(viewer):
            return 'ImageView' in viewer.__class__.__name__

        return super()._is_valid_item(viewer, locals())

    @observe('filters')
    def _on_viewers_changed(self, msg=None):
        # NOTE: _on_viewers_changed is passed without a msg object during init
        # list of dictionaries with id, ref, ref_or_id
        manual_items = [{'label': label} for label in self.manual_options]
        self.items = manual_items + [{k: v for k, v in vd.items() if k != 'viewer'}
                                     for vd in self.viewer_dicts if self._is_valid_item(vd['viewer'])] # noqa
        self._apply_default_selection()


class ViewerSelectMixin(VuetifyTemplate, HubListener):
    """
    Applies the ViewerSelect component as a mixin in the base plugin.  This
    automatically adds traitlets as well as new properties to the plugin with minimal
    extra code.  For multiple instances or custom traitlet names/defaults, use the
    component instead.

    To use in a plugin:

    * add ``ViewerSelectMixin`` as a mixin to the class
    * use the traitlets available from the plugin or properties/methods available from
      ``plugin.viewer``.

    Example template (label and hint are optional)::

      <plugin-viewer-select
        :items="viewer_items"
        :selected.sync="viewer_selected"
        label="Viewer"
        hint="Select viewer."
      />

    """
    viewer_items = List().tag(sync=True)
    viewer_selected = Any().tag(sync=True)
    viewer_multiselect = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.viewer = ViewerSelect(self, 'viewer_items', 'viewer_selected', 'viewer_multiselect')


class DatasetSelect(BaseSelectPluginComponent):
    """
    Traitlets (in the object, custom traitlets in the plugin):

    * ``items`` (list of dicts with keys: label)
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
    def __init__(self, plugin, items, selected,
                 filters=['not_from_plugin_model_fitting', 'layer_in_viewers'],
                 default_mode='first'):
        super().__init__(plugin, items=items, selected=selected, filters=filters,
                         default_mode=default_mode)
        self._cached_properties += ["selected_dc_item"]
        # Add/Remove Data are triggered when checked/unchecked from viewers
        self.hub.subscribe(self, AddDataMessage, handler=self._on_data_changed)
        self.hub.subscribe(self, RemoveDataMessage, handler=self._on_data_changed)
        self.hub.subscribe(self, DataCollectionDeleteMessage, handler=self._on_data_changed)

        # initialize items from original viewers
        self._on_data_changed()

    @property
    def default_data_cls(self):
        if self.app.config == 'imviz':
            return None
        return Spectrum1D

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
            if viewer_ref is None:
                # image viewers might not have a reference, but get_data_from_viewer
                # does not take id
                continue
            match = self.app.get_data_from_viewer(viewer_ref, data_label=self.selected)
            if match is not None:
                if hasattr(match, 'get_object'):
                    # cube viewers return the data collection instance from get_data_from_viewer
                    return match.get_object(cls=self.default_data_cls)
                return match
        # handle the case of empty Application with no viewer, we'll just pull directly
        # from the data collection
        return self.get_object(cls=self.default_data_cls)

    def _is_valid_item(self, data):
        def not_from_plugin(data):
            return data.meta.get('Plugin', None) is None

        def not_from_plugin_model_fitting(data):
            return data.meta.get('Plugin', None) != 'ModelFitting'

        def has_metadata(data):
            return hasattr(data, 'meta') and isinstance(data.meta, dict) and len(data.meta)

        def layer_in_viewers(data):
            if not len(self.app.get_viewer_reference_names()):
                # then this is a bar Application object, so ignore this filter
                return True
            for viewer in self.viewers:
                if data.label in [l.layer.label for l in viewer.layers]: # noqa E741
                    return True
            return False

        def layer_in_spectrum_viewer(data):
            if not len(self.app.get_viewer_reference_names()):
                # then this is a bar Application object, so ignore this filter
                return True
            return data.label in [l.layer.label for l in self.spectrum_viewer.layers] # noqa E741

        def is_image(data):
            return len(data.shape) == 3

        return super()._is_valid_item(data, locals())

    @observe('filters')
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
    component instead.

    To use in a plugin:

    * add ``DatasetSelectMixin`` as a mixin to the class
    * use the traitlets available from the plugin or properties/methods available from
      ``plugin.dataset``.

    Example template (label and hint are optional)::

      <plugin-dataset-select
        :items="dataset_items"
        :selected.sync="dataset_selected"
        label="Data"
        hint="Select data."
      />

    """
    dataset_items = List().tag(sync=True)
    dataset_selected = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # NOTE: cannot be named self.data or will conflict with existing self.data traitlet!
        self.dataset = DatasetSelect(self, 'dataset_items', 'dataset_selected')


class AutoLabel(BasePluginComponent):
    """
    Traitlets (in the object, custom traitlets in the plugin):

    * ``value`` (string: user-provided label for the results data-entry.  If ``auto``, changes
        to ``default`` will update ``value``.  Otherwise, changes to ``value`` will set
        ``auto`` to False.)
    * ``default`` (string: plugin-determined default label that will be synced to ``value``
        if/when ``auto`` is set to True)
    * ``auto`` (bool: whether to sync ``default`` to ``value``)
    * ``invalid_msg`` (string: validation string for the current value of ``value``.)

    Example template::

      <plugin-auto-label
        :value.sync="value"
        :default="comp_label_default"
        :auto.sync="comp_label_auto"
        :invalid_msg="invalid_msg"
        hint="Label hint."
      ></plugin-auto-label>

    """
    def __init__(self, plugin, value, default, auto,
                 invalid_msg):
        super().__init__(plugin, value=value,
                         default=default, auto=auto,
                         invalid_msg=invalid_msg)

        self.add_observe(default, self._on_set_to_default)
        self.add_observe(auto, self._on_set_to_default)

    def _on_set_to_default(self, msg={}):
        if self.auto:
            self.value = self.default


class AutoLabelMixin(VuetifyTemplate, HubListener):
    """
    Applies the AutoLabel component as a mixin in the base plugin.  This
    automatically adds traitlets as well as new properties to the plugin with minimal
    extra code.  For multiple instances or custom traitlet names/defaults, use the
    component instead.

    To use in a plugin:

    * add ``AutoLabelMixin`` as a mixin to the class
    * use the traitlets available from the plugin or properties/methods available from
      ``plugin.auto_label``.

    Example template::

      <plugin-auto-label
        :value.sync="label"
        :default="label_default"
        :auto.sync="label_auto"
        :invalid_msg="invalid_msg"
        hint="Label hint."
      ></plugin-auto-label>
    """
    label = Unicode().tag(sync=True)
    label_default = Unicode().tag(sync=True)
    label_auto = Bool(True).tag(sync=True)
    label_invalid_msg = Unicode('').tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auto_label = AddResults(self, 'label',
                                     'label_default', 'label_auto',
                                     'label_invalid_msg')


class AddResults(BasePluginComponent):
    """
    Traitlets (in the object, custom traitlets in the plugin):

    * ``label`` (string: user-provided label for the results data-entry.  If ``label_auto``, changes
        to ``label_default`` will update ``label``.  Otherwise, changes to ``label`` will set
        ``label_auto`` to False.)
    * ``label_default`` (string: plugin-determined default label that will be synced to ``label``
        if/when ``label_auto`` is set to True)
    * ``label_auto`` (bool: whether to sync ``label_default`` to ``label``)
    * ``label_invalid_msg`` (string: validation string for the current value of ``label``.  If
        not an empty string, calls to ``add_results_from_plugin`` will raise an error.)
    * ``label_overwrite`` (bool: whether the value of ``label`` already exists for a data-entry
        from the same plugin)
    * ``add_to_viewer_items`` (list of dicts: see ``ViewerSelect``)
    * ``add_to_viewer_selected`` (string: name of the viewer to add the results,
        see ``ViewerSelect``)


    Methods:

    * ``add_results_from_plugin``


    Example template::

      <plugin-add-results
        :label.sync="results_label"
        :label_default="results_label_default"
        :label_auto.sync="results_label_auto"
        :label_invalid_msg="results_label_invalid_msg"
        :label_overwrite="results_label_overwrite"
        label_hint="Label for the smoothed data"
        :add_to_viewer_items="add_to_viewer_items"
        :add_to_viewer_selected.sync="add_to_viewer_selected"
        action_label="Apply"
        action_tooltip="Apply the action to the data"
        @click:action="apply"
      ></plugin-add-results>

    """
    def __init__(self, plugin, label, label_default, label_auto,
                 label_invalid_msg, label_overwrite,
                 add_to_viewer_items, add_to_viewer_selected):
        super().__init__(plugin, label=label,
                         label_default=label_default, label_auto=label_auto,
                         label_invalid_msg=label_invalid_msg, label_overwrite=label_overwrite,
                         add_to_viewer_items=add_to_viewer_items,
                         add_to_viewer_selected=add_to_viewer_selected)

        # DataCollectionAdd/Delete are fired even if remain unchecked in all viewers
        self.hub.subscribe(self, DataCollectionAddMessage,
                           handler=lambda _: self._on_label_changed())
        self.hub.subscribe(self, DataCollectionDeleteMessage,
                           handler=lambda _: self._on_label_changed())

        self.viewer = ViewerSelect(plugin, add_to_viewer_items, add_to_viewer_selected,
                                   manual_options=['None'],
                                   default_mode=self._handle_default_viewer_selected)

        self.auto_label = AutoLabel(plugin, label, label_default, label_auto, label_invalid_msg)
        self.add_observe(label, self._on_label_changed)

    def _handle_default_viewer_selected(self, viewer_comp, is_valid):
        if len(viewer_comp.items) == 2:
            # then we're a switch, so we want to default to ON
            return viewer_comp.labels[1]
        else:
            # then we're a dropdown, so want to default to None and force the user to choose
            return 'None'

    def _on_label_changed(self, msg={}):
        if not len(self.label.strip()):
            # strip will raise the same error for a label of all spaces
            self.label_invalid_msg = 'label must be provided'
            return

        for data in self.app.data_collection:
            if self.label == data.label:
                if data.meta.get('Plugin', None) == self._plugin.__class__.__name__:
                    self.label_invalid_msg = ''
                    self.label_overwrite = True
                    return
                else:
                    self.label_invalid_msg = 'label already in use'
                    self.label_overwrite = False
                    return

        self.label_invalid_msg = ''
        self.label_overwrite = False

    def add_results_from_plugin(self, data_item):
        """
        Add ``data_item`` to the app's data_collection according to the default or user-provided
        label and adds to any requested viewers.
        """
        if self.label_invalid_msg:
            raise ValueError(self.label_invalid_msg)
        data_item.meta['Plugin'] = self._plugin.__class__.__name__
        if self.app.config == 'mosviz':
            data_item.meta['mosviz_row'] = self.app.state.settings['mosviz_row']

        replace = self.viewer.selected_reference != 'spectrum-viewer'

        if self.label in self.app.data_collection:
            self.app.remove_data_from_viewer(self.viewer.selected_reference, self.label)
            self.app.data_collection.remove(self.app.data_collection[self.label])

        self.app.add_data(data_item, self.label)

        if self.add_to_viewer_selected != 'None':
            # replace the contents in the selected viewer with the results from this plugin
            # TODO: switch to an instance/classname check?
            self.app.add_data_to_viewer(self.viewer.selected_id,
                                        self.label, clear_other_data=False)

            if replace:
                data_id = next((x['id'] for x in self.app.state.data_items
                                if x['name'] == self.label), None)
                self.app.vue_data_item_visibility({'id': self.viewer.selected_id,
                                                   'item_id': data_id,
                                                   'visible': True,
                                                   'replace': True})


class AddResultsMixin(VuetifyTemplate, HubListener):
    """
    Applies the AddResults component as a mixin in the base plugin.  This
    automatically adds traitlets as well as new properties to the plugin with minimal
    extra code.  For multiple instances or custom traitlet names/defaults, use the
    component instead.

    To use in a plugin:

    * add ``AddResultsMixin`` as a mixin to the class
    * use the traitlets available from the plugin or properties/methods available from
      ``plugin.add_results``.

    Example template::

      <plugin-add-results
        :label.sync="results_label"
        :label_default="results_label_default"
        :label_auto.sync="results_label_auto"
        :label_invalid_msg="results_label_invalid_msg"
        :label_overwrite="results_label_overwrite"
        label_hint="Label for the smoothed data"
        :add_to_viewer_items="add_to_viewer_items"
        :add_to_viewer_selected.sync="add_to_viewer_selected"
        action_label="Apply"
        action_tooltip="Apply the action to the data"
        @click:action="apply"
      ></plugin-add-results>

    """
    results_label = Unicode().tag(sync=True)
    results_label_default = Unicode().tag(sync=True)
    results_label_auto = Bool(True).tag(sync=True)
    results_label_invalid_msg = Unicode('').tag(sync=True)
    results_label_overwrite = Bool().tag(sync=True)

    add_to_viewer_items = List().tag(sync=True)
    add_to_viewer_selected = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_results = AddResults(self, 'results_label',
                                      'results_label_default', 'results_label_auto',
                                      'results_label_invalid_msg', 'results_label_overwrite',
                                      'add_to_viewer_items', 'add_to_viewer_selected')


class PlotOptionsSyncState(BasePluginComponent):
    """
    """
    def __init__(self, plugin, viewer_select, layer_select, glue_name,
                 value, sync, state_filter=None):
        super().__init__(plugin, value=value, sync=sync)
        self._state_filter = state_filter
        self._linked_states = []
        self._processing_change_from_glue = False
        self._processing_change_to_glue = False
        self._cached_properties = ["subscribed_states", "subscribed_icons"]

        self._viewer_select = viewer_select
        self._layer_select = layer_select
        self._glue_name = glue_name
        self.add_observe(viewer_select._plugin_traitlets['selected'], self._on_viewer_layer_changed)
        self.add_observe(layer_select._plugin_traitlets['selected'], self._on_viewer_layer_changed)
        self.add_observe(value, self._on_value_changed)
        self._on_viewer_layer_changed()

    def state_filter(self, state):
        if self._state_filter is None:
            return True
        return self._state_filter(state)

    @cached_property
    def subscribed_states(self):
        # states object that according to the viewer selection, we *should*
        # link if this entry is found there
        viewers = self._viewer_select.selected_obj
        if not isinstance(viewers, list):
            # which is the case for single-select
            viewers = [viewers]

        def _state_item(item):
            if isinstance(item, list):
                return [_state_item(item_i) for item_i in item]
            elif item is None:
                return None
            else:
                return item.state

        viewer_states = [_state_item(viewer) for viewer in viewers]

        layer_labels = self._layer_select.selected
        if not isinstance(layer_labels, list):
            layer_labels = [layer_labels]

        # NOTE: accessing from self._layer_select.selected_obj would give us a per-viewer
        # list, but we need a per-selected-layer list.
        layer_states = []
        for selected_layer_label in layer_labels:
            layer_states.append([])
            for viewer in viewers:
                for layer in viewer.layers:
                    if layer.layer.label == selected_layer_label:
                        layer_states[-1].append(layer.state)

        # subscribed states can still be nested list
        return viewer_states + layer_states

    @cached_property
    def subscribed_icons(self):
        # dictionary items giving information about the entries in subscribed_states
        viewer_icons = self._viewer_select.selected_item.get('icon', [])
        if not isinstance(viewer_icons, list):
            viewer_icons = [viewer_icons]

        layer_icons = self._layer_select.selected_item.get('icon', [])
        if not isinstance(layer_icons, list):
            layer_icons = [layer_icons]

        return viewer_icons + layer_icons

    @property
    def linked_states(self):
        # access glue state objects for which the callbacks are currently connected
        return self._linked_states

    def _get_glue_value(self, state):
        if self._glue_name == 'cmap':
            return getattr(state, self._glue_name).name
        return getattr(state, self._glue_name)

    def _get_glue_choices(self, state):
        if self._glue_name == 'cmap':
            return [{'text': cmap[0], 'value': cmap[1].name} for cmap in colormaps.members]
        elif self._glue_name == 'color_mode':
            return [{'text': 'Colormap', 'value': 'Colormaps'},
                    {'text': 'Monochromatic', 'value': 'One color per layer'}]
        else:
            values, labels = _get_glue_choices(state, self._glue_name)
            return [{'text': l, 'value': v} for v, l in zip(values, labels)]

    def _on_viewer_layer_changed(self, msg=None):
        self._clear_cache(*self._cached_properties)

        # clear existing callbacks - we'll re-create those we need later
        for state in self.linked_states:
            state.remove_callback(self._glue_name, self._on_glue_value_changed)

        in_subscribed_states = False
        icons = []
        current_glue_values = []
        self._linked_states = []
        for states, icon in zip(self.subscribed_states, self.subscribed_icons):
            if not isinstance(states, list):
                states = [states]

            for state in states:
                if state is None or not self.state_filter(state):
                    continue
                if self._glue_name is None or not hasattr(state, self._glue_name):
                    continue

                in_subscribed_states = True
                if icon not in icons:
                    icons.append(icon)
                current_glue_values.append(self._get_glue_value(state))
                self._linked_states.append(state)  # these will be iterated when value is set
                state.add_callback(self._glue_name, self._on_glue_value_changed)

                if self.sync.get('choices') is None and \
                        (hasattr(getattr(type(state), self._glue_name), 'get_display_func')
                         or self._glue_name == 'cmap'):
                    # then we can access and populate the choices.  We are assuming here
                    # that each state-instance with this same name will have the same
                    # choices and that those will not change.  If we ever hookup options
                    # with changing choices, we'll need additional logic to sync to those
                    # and handle mixed state in the choices...
                    self.sync = {**self.sync, 'choices': self._get_glue_choices(state)}

        self.sync = {**self.sync,
                     'in_subscribed_states': in_subscribed_states,
                     'icons': icons,
                     'mixed': len(np.unique(current_glue_values, axis=0)) > 1}

        if len(current_glue_values):
            # sync the initial value of the widget, avoiding recursion
            self._on_glue_value_changed(current_glue_values[0])

    def _update_mixed_state(self):
        if len(self.linked_states) <= 1:
            mixed = False
        else:
            current_glue_values = []
            for state in self.linked_states:
                current_glue_values.append(self._get_glue_value(state))
                mixed = len(np.unique(current_glue_values, axis=0)) > 1
        self.sync = {**self.sync,
                     'mixed': mixed}

    def _on_value_changed(self, msg):
        if self._processing_change_from_glue:
            return

        self._processing_change_to_glue = True
        for glue_state in self.linked_states:
            if self._glue_name == 'cmap':
                cmap = None
                for member in colormaps.members:
                    if member[1].name == msg['new']:
                        cmap = member[1]
                        break
                setattr(glue_state, self._glue_name, cmap)
            else:
                setattr(glue_state, self._glue_name, msg['new'])
        # need to recompute mixed state
        self._update_mixed_state()
        self._processing_change_to_glue = False

    def _on_glue_value_changed(self, value):
        if self._processing_change_to_glue:
            return

        self._processing_change_from_glue = True
        if "Colormap" in value.__class__.__name__:  # TODO: better logic
            value = str(value)
        elif isinstance(self.value, (int, float)) and self._glue_name != 'percentile':
            # glue might pass us ints for float or vice versa, but our traitlets care
            # so let's cast to the type expected by the traitlet to avoid having to
            # use Any traitlets for all of these.  We skip percentile as that needs
            # to be an Any traitlet in order to handle "Custom"
            value = type(self.value)(value)
        self.value = value
        # need to recompute mixed state
        self._update_mixed_state()
        self._processing_change_from_glue = False

    def unmix_state(self):
        self._on_value_changed({'new': self.value})
        self.sync = {**self.sync,
                     'mixed': False}
