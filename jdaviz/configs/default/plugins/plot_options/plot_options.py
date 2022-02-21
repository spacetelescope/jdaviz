from traitlets import Any, Bool, Dict, Float, Int, List, Unicode, observe

from glue.core.message import (SubsetCreateMessage, SubsetUpdateMessage, SubsetDeleteMessage)
from glue_jupyter.vuetify_helpers import link_glue, link_glue_choices

from jdaviz.core.events import (ViewerAddedMessage, ViewerRemovedMessage,
                                AddDataMessage, RemoveDataMessage,
                                PlotOptionsSelectViewerMessage)
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin

__all__ = ['PlotOptions']


def make_layer_panel(viewer, layer_artist):
    # modified from glue-jupyter layer_options.py
    widget_cls = viewer._layer_style_widget_cls
    if isinstance(widget_cls, dict):
        return widget_cls[type(layer_artist)](layer_artist.state)
    else:
        return widget_cls(layer_artist.state)


@tray_registry('g-plot-options', label="Plot Options")
class PlotOptions(TemplateMixin):
    template_file = __file__, "plot_options.vue"
    viewer_items = List([]).tag(sync=True)
    selected_viewers = List([]).tag(sync=True)
    layer_items = List([]).tag(sync=True)
    selected_layers = List([]).tag(sync=True)

#    # store a list of items that are in a "mixed state"
#    mixed_state = List().tag(sync=True)

    # store a list of which widgets we want to show (based on the viewer type)
    # this gets populated automatically when the viewer selection changes, as do
    # the hooks between the glue-state and the traitlet items defined below
    viewer_state_items = List().tag(sync=True)

    # example of viewer bool state - perhaps we can create a helper to create the _mixed and _vs?
    show_axes = Bool().tag(sync=True)
    show_axes_mixed = Bool().tag(sync=True)
    show_axes_vs = List().tag(sync=True)

    # example of viewer choice state
    function_items = List().tag(sync=True)
    function_selected = Int(allow_none=True).tag(sync=True)
    function_mixed = Bool().tag(sync=True)
    function_vs = List().tag(sync=True)

    # same for layer options as above
    layer_state_items = List().tag(sync=True)

    linewidth = Int().tag(sync=True)
    # TODO: change from _vs to _ls???
    linewidth_mixed = Bool().tag(sync=True)
    linewidth_vs = List().tag(sync=True)

    percentile_items = List().tag(sync=True)
    percentile_selected = Int(allow_none=True).tag(sync=True)
    percentile_mixed = Bool().tag(sync=True)
    percentile_vs = List().tag(sync=True)

#    cmap_items = List().tag(sync=True)
#    cmap_selected = Int(allow_none=True).tag(sync=True)
#    cmap_vs = List().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hub.subscribe(self, ViewerAddedMessage,
                           handler=lambda _: self._on_viewers_changed())
        self.hub.subscribe(self, ViewerRemovedMessage,
                           handler=lambda _: self._on_viewers_changed())
        self.hub.subscribe(self, AddDataMessage,
                           handler=lambda _: self._selected_viewers_changed())
        self.hub.subscribe(self, RemoveDataMessage,
                           handler=lambda _: self._selected_viewers_changed())
        self.hub.subscribe(self, SubsetCreateMessage,
                           handler=lambda _: self._selected_viewers_changed())
        self.hub.subscribe(self, SubsetUpdateMessage,
                           handler=lambda _: self._selected_viewers_changed())
        self.hub.subscribe(self, SubsetDeleteMessage,
                           handler=lambda _: self._selected_viewers_changed())
        self.hub.subscribe(self, PlotOptionsSelectViewerMessage,
                           handler=self._on_select_viewer_message)

        # initialize viewer_items from original viewers
        self._on_viewers_changed()

    def _on_viewers_changed(self):
        self.viewer_items = self.app.get_viewer_reference_names()

        # TODO: default for original
#        if self.selected_viewers not in self.viewer_items:
#            # default to first entry, will trigger _on_viewer_select to set layer defaults
#            self.selected_viewers = self.viewer_items[0] if len(self.viewer_items) else ""

    def _on_select_viewer_message(self, msg):
        # message from elsewhere requesting to change the selected viewer
        self.selected_viewers = msg.viewer if isinstance(msg.viewer, list) else [msg.viewer]

    def _clear_glue_links(self, state_item):
#        print(f"*** _clear_glue_links for {state_item}")
        for handler in self._trait_notifiers.get(state_item, {}).get('change', []):
            if handler.__name__ == 'to_glue_state':
                self.unobserve(handler, state_item)
#            else:
#                print(f"*** ignoring {handler} on {state_item}")

    def _link_state_items(self, states, states_names, items_list, items_dict, unmix=False):
#        mixed_state = self.mixed_state
        ret_state_items = []
        for state_item, state_type in items_dict.items():
            this_item_inds = []
            this_item_curr_values = []
            # clear existing glue links, we'll create a new link for each applicable
            # selected viewer
            self._clear_glue_links(state_item)

            # loop through to check current values and determine if we should link
            # or if we need to store as a mixed state
            for state, state_name in zip(states, states_names):
                if hasattr(state, state_item):
                    # store this in the list of items that will be shown in the UI
                    ret_state_items.append(state_item)
                    # append the index of this viewer (we'll handle the +1 in vue)
                    this_item_inds.append(items_list.index(state_name))
                    # store the current value - to determine if we're in a mixed state
                    this_item_curr_values.append(getattr(state, state_item))

            if len(list(set(this_item_curr_values))) == 1 or unmix == state_item:
                # then all values are synced, so we can link and expose
#                if state_item in mixed_state:
#                    mixed_state.remove(state_item)
                setattr(self, f'{state_item}_mixed', False)
                for state, state_name in zip(states, states_names):
                    if hasattr(state, state_item):
                        if state_type == 'choice':
                            # NOTE: different arg order than link_glue...
                            link_glue_choices(self, state, state_item)
                        else:
                            link_glue(self, state_item, state)
            elif len(this_item_curr_values):
                # then we're in a mixed state.  Current links have already been
                # cleared, so we'll set the traitlet to the default value so the
                # widget shows what WILL happen if syncing, and then append to the
                # list that the UI will use to disable the entry.
                setattr(self, state_item, this_item_curr_values[0])
#                if state_item not in mixed_state:
#                    mixed_state.append(state_item)
                #print(f"*** {state_item} is in a mixed state")
                setattr(self, f'{state_item}_mixed', True)

            # set the indices of the viewers to show in the UI for this item
            setattr(self, f'{state_item}_vs', this_item_inds)

#        if len(mixed_state): print("*** mixed state:", mixed_state)
#        self.mixed_state = mixed_state

        return ret_state_items

    @observe("selected_viewers")
    def _selected_viewers_changed(self, event={}, unmix=False):
        selected_viewers = event.get('new', self.selected_viewers)
        viewer_states = [self.app.get_viewer(viewer_name).state for viewer_name in selected_viewers]

        # update the list of options that should be shown in the UI, handle glue linking, etc
        self.viewer_state_items = self._link_state_items(viewer_states,
                                                         selected_viewers,
                                                         self.viewer_items,
                                                         {'show_axes': 'bool',
                                                          'function': 'choice'},  # only include function for cubeviz (JDAT-2018)
                                                         unmix=unmix)

        # TODO: try to ditch the double-loop
        layer_items = []
        for viewer_name in selected_viewers:
            for layer in self.app.get_viewer(viewer_name).layers:
                if layer.layer.label not in layer_items:
                    # store the name of the layer, this will populate the dropdown
                    layer_items.append(layer.layer.label)
        self.layer_items = layer_items

        # TODO: defaults for selected_layers (clear out any no longer available, etc)

        # force layer_state_items to update from a change in viewers
        self._selected_layers_changed(unmix=unmix)

    @observe("selected_layers")
    def _selected_layers_changed(self, event={}, unmix=False):
        selected_layers = event.get('new', self.selected_layers)
        selected_layers_exp = []
        layer_states_exp = []
        for viewer_name in self.selected_viewers:
            for layer in self.app.get_viewer(viewer_name).layers:
                if layer.layer.label not in selected_layers:
                    continue
                selected_layers_exp.append(layer.layer.label)
                layer_states_exp.append(layer.state)

        # update the list of options that should be shown in the UI, handle glue linking, etc
        self.layer_state_items = self._link_state_items(layer_states_exp,
                                                        selected_layers_exp,
                                                        self.layer_items,
                                                        {'linewidth': 'int',
                                                         'percentile': 'choice'},
                                                        unmix=unmix)

        # here we would do similar and loop through the items we want to provide for layers
        # populate layer_state_items and handling unlinking/linking to the glue state

    def vue_unmix_state(self, state_item):
        current_value = getattr(self, state_item)
        self._selected_viewers_changed(unmix=state_item)
        # make sure the final value is the one that was expected according to the UI
        setattr(self, state_item, current_value)

#    @observe('function_selected')
#    def _on_change_traitlet_require_reset_yzoom(self, event):
#        # TODO: need to make sure that the data has changed first... could probably flip a switch saying that the next change to data requires a zoom-reset?  Or fix this upstream
#        state_item = event['name'].strip('_selected')
#        applicable_viewer_inds = getattr(self, f'{state_item}_vs')
#        for viewer_ind in applicable_viewer_inds:
#            # TODO: keep x-limits?
#            self.app.get_viewer(self.viewer_items[viewer_ind]).state.reset_limits()
