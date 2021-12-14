from astropy import units as u
from glue.core.message import (DataCollectionAddMessage,
                               DataCollectionDeleteMessage)
from glue.core import Data
from glue.core.link_helpers import LinkSame
from specutils import Spectrum1D
from specutils import SpectralRegion
from specutils.manipulation import spectral_slab
from traitlets import List, Unicode, Int, Any, Bool, observe
from regions import RectanglePixelRegion

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin

__all__ = ['Collapse']


spaxel = u.def_unit('spaxel', 1 * u.Unit(""))
u.add_enabled_units([spaxel])


# Mapping of pixel axes before and after collapse, as a function of selected axis
AXES_MAPPING = [((1, 2), (0, 1)), ((0, 2), (0, 1)), ((0, 1), (0, 1))]


@tray_registry('g-collapse', label="Collapse")
class Collapse(TemplateMixin):
    template_file = __file__, "collapse.vue"
    data_items = List([]).tag(sync=True)
    selected_data_item = Unicode().tag(sync=True)
    axes = List([]).tag(sync=True)
    selected_axis = Int(0).tag(sync=True)
    funcs = List(['Mean', 'Median', 'Min', 'Max', 'Sum']).tag(sync=True)
    selected_func = Unicode('Mean').tag(sync=True)

    # add/replace results for selected_axis != 0
    add_replace_results = Bool(True).tag(sync=True)

    # selected_viewer for selected_axis == 0
    # NOTE: this is currently cubeviz-specific so will need to be updated
    # to be config-specific if using within other viewer configurations.
    viewer_to_id = {'Left': 'cubeviz-0', 'Center': 'cubeviz-1', 'Right': 'cubeviz-2'}
    viewers = List(['None', 'Left', 'Center', 'Right']).tag(sync=True)
    selected_viewer = Unicode('None').tag(sync=True)

    spectral_min = Any().tag(sync=True)
    spectral_max = Any().tag(sync=True)
    spectral_unit = Unicode().tag(sync=True)
    spectral_subset_items = List(["None"]).tag(sync=True)
    selected_subset = Unicode("None").tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hub.subscribe(self, DataCollectionAddMessage,
                           handler=self._on_data_updated)
        self.hub.subscribe(self, DataCollectionDeleteMessage,
                           handler=self._on_data_updated)

        self._selected_data = None
        self._spectral_subsets = {}
        self._label_counter = 0

    def _on_data_updated(self, msg):
        self.data_items = [x.label for x in self.data_collection]
        # Default to selecting the first loaded cube
        if self._selected_data is None:
            for i in range(len(self.data_items)):
                try:
                    self.selected_data_item = self.data_items[i]
                except (ValueError, TypeError):
                    continue

    @observe('selected_data_item')
    def _on_data_item_selected(self, event):
        self._selected_data = next((x for x in self.data_collection
                                    if x.label == event['new']))

        # Also set the spectral min and max to default to the full range
        cube = self._selected_data.get_object(cls=Spectrum1D, statistic=None)
        self.selected_subset = "None"
        self.spectral_min = cube.spectral_axis[0].value
        self.spectral_max = cube.spectral_axis[-1].value
        self.spectral_unit = str(cube.spectral_axis.unit)

        # FIXME: Re-enable spatial-spectral collapse
        # self.axes = list(range(len(self._selected_data.shape)))
        self.axes = [0]

    @observe("selected_subset")
    def _on_subset_selected(self, event):
        # If "None" selected, reset based on bounds of selected data
        if self.selected_subset == "None":
            cube = self._selected_data.get_object(cls=Spectrum1D, statistic=None)
            self.spectral_min = cube.spectral_axis[0].value
            self.spectral_max = cube.spectral_axis[-1].value
        else:
            spec_sub = self._spectral_subsets[self.selected_subset]
            unit = u.Unit(self.spectral_unit)
            spec_reg = SpectralRegion.from_center(spec_sub.center.x * unit,
                                                  spec_sub.width * unit)
            self.spectral_min = spec_reg.lower.value
            self.spectral_max = spec_reg.upper.value

    def vue_list_subsets(self, event):
        """Populate the spectral subset selection dropdown"""
        temp_subsets = self.app.get_subsets_from_viewer("spectrum-viewer",
                                                        subset_type="spectral")
        temp_dict = {}
        # Attempt to filter out spatial subsets
        for key, region in temp_subsets.items():
            if type(region) == RectanglePixelRegion:
                temp_dict[key] = region
        self._spectral_subsets = temp_dict
        self.spectral_subset_items = ["None"] + sorted(temp_dict.keys())

    def vue_collapse(self, *args, **kwargs):
        try:
            spec = self._selected_data.get_object(cls=Spectrum1D, statistic=None)
        except AttributeError:
            snackbar_message = SnackbarMessage(
                "Unable to perform collapse over selected data.",
                color="error",
                sender=self)
            self.hub.broadcast(snackbar_message)

            return

        # If collapsing over the spectral axis, cut out the desired spectral
        # region. Defaults to the entire spectrum.
        if self.selected_axis == 0:
            spec_min = float(self.spectral_min) * u.Unit(self.spectral_unit)
            spec_max = float(self.spectral_max) * u.Unit(self.spectral_unit)
            spec = spectral_slab(spec, spec_min, spec_max)

        # FIXME: Does not work.
        # collapsed_spec = spec.collapse(self.selected_func.lower(), axis=self.selected_axis)
        # data = Data(coords=collapsed_spec.wcs)
        # data['flux'] = collapsed_spec.filled_data[...]
        # data.get_component('flux').units = str(collapsed_spec.unit)
        # data.meta.update(collapsed_spec.meta)

        # FIXME: Spatial-spatial image only.
        collapsed_spec = spec.collapse(self.selected_func.lower(), axis=-1)  # Quantity
        data = Data()
        data['flux'] = collapsed_spec.value
        data.get_component('flux').units = str(collapsed_spec.unit)

        self._label_counter += 1
        label = f"Collapsed {self._label_counter} {self._selected_data.label}"

        self.data_collection[label] = data

        # FIXME: Does not work.
        # Link the new dataset pixel-wise to the original dataset. In general
        # direct pixel to pixel links are the most efficient and should be
        # used in cases like this where we know there is a 1-to-1 mapping of
        # pixel coordinates. Here which axes are linked to which depends on
        # the selected axis.
        # (i1, i2), (i1c, i2c) = AXES_MAPPING[self.selected_axis]

        # FIXME: Spatial-spatial image only.
        (i1, i2), (i1c, i2c) = AXES_MAPPING[-1]

        pix_id_1 = self._selected_data.pixel_component_ids[i1]
        pix_id_1c = self.data_collection[label].pixel_component_ids[i1c]
        pix_id_2 = self._selected_data.pixel_component_ids[i2]
        pix_id_2c = self.data_collection[label].pixel_component_ids[i2c]

        self.data_collection.add_link([LinkSame(pix_id_1, pix_id_1c),
                                       LinkSame(pix_id_2, pix_id_2c)])

        snackbar_message = SnackbarMessage(
            f"Data set '{self._selected_data.label}' collapsed successfully.",
            color="success",
            sender=self)
        self.hub.broadcast(snackbar_message)

        if self.selected_axis == 0 and self.selected_viewer != 'None':
            # replace the contents in the selected viewer with the results from this plugin
            self.app.add_data_to_viewer(self.viewer_to_id.get(self.selected_viewer),
                                        label, clear_other_data=True)

        elif self.selected_axis != 0 and self.add_replace_results:
            self.app.add_data_to_viewer('spectrum-viewer', label)
