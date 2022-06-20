from glue.core.message import EditSubsetMessage, SubsetUpdateMessage
from glue.core.edit_subset_mode import (AndMode, AndNotMode, OrMode,
                                        ReplaceMode, XorMode)
from glue.core.subset import RoiSubsetState, RangeSubsetState, CompositeSubsetState
from glue_jupyter.widgets.subset_mode_vuetify import SelectionModeMenu
from traitlets import List, Unicode, Bool, observe

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
    subset_selected = Unicode("Create new").tag(sync=True)
    mode_selected = Unicode('add').tag(sync=True)
    show_region_info = Bool(True).tag(sync=True)
    subset_types = List([]).tag(sync=True)
    subset_definitions = List([]).tag(sync=True)
    has_subset_details = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.components = {
            'g-subset-mode': SelectionModeMenu(session=self.session)
        }

        self.session.hub.subscribe(self, EditSubsetMessage,
                                   handler=self._sync_selected_from_state)
        self.session.hub.subscribe(self, SubsetUpdateMessage,
                                   handler=self._on_subset_update)

        self.subset_select = SubsetSelect(self,
                                          'subset_items',
                                          'subset_selected',
                                          default_text="Create New")

    def _sync_selected_from_state(self, *args):
        if not hasattr(self, 'subset_select'):
            # during initial init, this can trigger before the component is initialized
            return
        if self.session.edit_subset_mode.edit_subset == []:
            if self.subset_selected != self.subset_select.default_text:
                self.subset_selected = self.subset_select.default_text
                self.show_region_info = False
        else:
            new_label = self.session.edit_subset_mode.edit_subset[0].label
            if new_label != self.subset_selected:
                if new_label not in [s['label'] for s in self.subset_items]:
                    self._sync_available_from_state()
                self.subset_selected = self.session.edit_subset_mode.edit_subset[0].label
                self.show_region_info = True

    def _on_subset_update(self, *args):
        self._sync_selected_from_state(*args)
        self._get_subset_definition(*args)
        subset_to_update = self.session.edit_subset_mode.edit_subset[0]
        self.subset_select._update_subset(subset_to_update, attribute="type")

    def _sync_available_from_state(self, *args):
        if not hasattr(self, 'subset_select'):
            # during initial init, this can trigger before the component is initialized
            return
        self.subset_items = [{'label': self.subset_select.default_text}] + [
                             self.subset_select._subset_to_dict(subset) for subset in
                             self.data_collection.subset_groups]

    @observe('subset_selected')
    def _sync_selected_from_ui(self, change):
        if not hasattr(self, 'subset_select'):
            # during initial init, this can trigger before the component is initialized
            return

        if change['new'] != self.subset_select.default_text:
            self._get_subset_definition(change['new'])
        self.show_region_info = change['new'] != self.subset_select.default_text
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

    def _unpack_nested_subset(self, subset_state):
        '''
        Navigate through the tree of subset states for composite
        subsets made up of multiple regions.
        '''
        if isinstance(subset_state, CompositeSubsetState):
            self._unpack_nested_subset(subset_state.state1)
            self._unpack_nested_subset(subset_state.state2)
        else:
            if subset_state is not None:
                self._get_subset_subregion_definition(subset_state)

    def _get_subset_subregion_definition(self, subset_state):
        """
        Get the type and parameters for a single region in the subset. Note that
        the string type and operation (if in a composite subset) need to be stored
        separately from the float parameters for display reasons.
        """
        subset_type = {}
        subset_definition = None

        if isinstance(subset_state, RoiSubsetState):
            subset_classname = subset_state.roi.__class__.__name__
            if subset_classname == "CircularROI":
                x, y = subset_state.roi.get_center()
                subset_definition = {"X Center": x,
                                     "Y Center": y,
                                     "Radius": subset_state.roi.radius}

            elif subset_classname == "RectangularROI":
                subset_definition = {}
                for att in ("Xmin", "Xmax", "Ymin", "Ymax"):
                    subset_definition[att] = getattr(subset_state.roi, att.lower())

            elif subset_classname == "EllipticalROI":
                subset_definition = {"X Center": subset_state.roi.xc,
                                     "Y Center": subset_state.roi.yc,
                                     "X Radius": subset_state.roi.radius_x,
                                     "Y Radius": subset_state.roi.radius_y}
            subset_type["Subset type"] = subset_classname

        elif isinstance(subset_state, RangeSubsetState):
            subset_definition = {"Upper bound": subset_state.hi,
                                 "Lower bound": subset_state.lo}
            subset_type["Subset type"] = "Range"

        if subset_definition is not None and subset_definition not in self.subset_definitions:
            self.subset_definitions = self.subset_definitions + [subset_definition]
            self.subset_types = self.subset_types + [subset_type]

    def _get_subset_definition(self, *args):
        """
        Retrieve the parameters defining the selected subset, for example the
        upper and lower bounds for a simple spectral subset.
        """
        self.subset_definitions = []
        self.subset_types = []
        subset_group = [s for s in self.app.data_collection.subset_groups if
                        s.label == self.subset_selected][0]
        subset_state = subset_group.subset_state

        self._unpack_nested_subset(subset_state)
