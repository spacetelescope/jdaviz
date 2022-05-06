from glue.core.message import EditSubsetMessage, SubsetUpdateMessage
from glue.core.edit_subset_mode import (AndMode, AndNotMode, OrMode,
                                        ReplaceMode, XorMode)
from glue.core.subset import (RoiSubsetState, RangeSubsetState,
                              OrState, AndState, XorState, InvertState)
from glue_jupyter.widgets.subset_mode_vuetify import SelectionModeMenu
from traitlets import List, Unicode, Bool, Dict, observe

from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin, SubsetSelect

__all__ = ['SubsetPlugin']

SUBSET_MODES = {
    'replace': ReplaceMode,
    'add': OrMode,
    'and': AndMode,
    'xor': XorMode,
    'remove': AndNotMode
}


@tray_registry('g-subset-plugin', label="Subset Tools")
class SubsetPlugin(TemplateMixin):
    template_file = __file__, "subset_plugin.vue"
    select = List([]).tag(sync=True)
    subset_items = List([]).tag(sync=True)
    subset_selected = Unicode("No selection (create new)").tag(sync=True)
    mode_selected = Unicode('add').tag(sync=True)
    show_region_info = Bool(False).tag(sync=True)
    subset_classname = Unicode('').tag(sync=True)
    subset_definition = Dict({}).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.components = {
            'g-subset-mode': SelectionModeMenu(session=self.session)
        }

        self.session.hub.subscribe(self, EditSubsetMessage,
                                   handler=self._sync_selected_from_state)
        self.session.hub.subscribe(self, SubsetUpdateMessage,
                                   handler=self._get_region_definition)

        self.no_selection_text = "Create new"
        self.subset_select = SubsetSelect(self,
                                          'subset_items',
                                          'subset_selected',
                                          default_text=self.no_selection_text)

    def _sync_selected_from_state(self, *args):
        if self.session.edit_subset_mode.edit_subset == []:
            if self.subset_selected != self.no_selection_text:
                self.subset_selected = self.no_selection_text
                self.show_region_info = False
        else:
            new_label = self.session.edit_subset_mode.edit_subset[0].label
            if new_label != self.subset_selected:
                if new_label not in [s['label'] for s in self.subset_items]:
                    self._sync_available_from_state()
                self.subset_selected = self.session.edit_subset_mode.edit_subset[0].label
                self.show_region_info = True

    def _sync_available_from_state(self, *args):
        self.subset_items = [{'label': self.no_selection_text}] + [
                             self.subset_select._subset_to_dict(subset) for subset in
                             self.data_collection.subset_groups]

    @observe('subset_selected')
    def _sync_selected_from_ui(self, change):
        if change['new'] != self.no_selection_text:
            self._get_region_definition(change['new'])
        self.show_region_info = change['new'] != self.no_selection_text
        m = [s for s in self.app.data_collection.subset_groups if s.label == change['new']]
        if m != self.session.edit_subset_mode.edit_subset:
            self.session.edit_subset_mode.edit_subset = m

    '''
    # This will be needed once we use a dropdown instead of the actual
    # g-subset-mode component
    @observe("mode_selected")
    def _mode_selected_changed(self, event={}):
        if self.session.edit_subset_mode != self.mode_selected:
            self.session.edit_subset_mode = self.mode_selected
    '''

    def _get_region_definition(self, *args):
        self.subset_definition = {}
        subset_group = [s for s in self.app.data_collection.subset_groups if
                        s.label == self.subset_selected][0]
        subset_state = subset_group.subset_state
        subset_class = subset_state.__class__

        if subset_class in (OrState, AndState, XorState, InvertState):
            self.subset_classname = "Compound Subset"
        else:
            if isinstance(subset_state, RoiSubsetState):
                self.subset_classname = subset_state.roi.__class__.__name__
                if self.subset_classname == "CircularROI":
                    x, y = subset_state.roi.get_center()
                    self.subset_definition = {"X Center": x,
                                              "Y Center": y,
                                              "Radius": subset_state.roi.radius}
                elif self.subset_classname == "RectangularROI":
                    temp_def = {}
                    for att in ("Xmin", "Xmax", "Ymin", "Ymax"):
                        temp_def[att] = getattr(subset_state.roi, att.lower())
                    self.subset_definition = temp_def
                elif self.subset_classname == "EllipticalROI":
                    self.subset_definition = {"X Center": subset_state.roi.xc,
                                              "Y Center": subset_state.roi.yc,
                                              "X Radius": subset_state.roi.radius_x,
                                              "Y Radius": subset_state.roi.radius_y}
            elif isinstance(subset_state, RangeSubsetState):
                self.subset_classname = "Range"
                self.subset_definition = {"Upper bound": subset_state.hi,
                                          "Lower bound": subset_state.lo}
