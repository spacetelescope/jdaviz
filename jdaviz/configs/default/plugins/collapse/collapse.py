import warnings

from astropy import units as u
from glue.core.message import (DataCollectionAddMessage,
                               DataCollectionDeleteMessage)
from glue.core import Data
from glue.core.link_helpers import LinkSame
from specutils import Spectrum1D
from specutils.manipulation import spectral_slab
from traitlets import List, Unicode, observe

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, SpectralSubsetSelectMixin

__all__ = ['Collapse']


@tray_registry('g-collapse', label="Collapse")
class Collapse(PluginTemplateMixin, SpectralSubsetSelectMixin):
    template_file = __file__, "collapse.vue"
    data_items = List([]).tag(sync=True)
    selected_data_item = Unicode().tag(sync=True)
    funcs = List(['Mean', 'Median', 'Min', 'Max', 'Sum']).tag(sync=True)
    selected_func = Unicode('Sum').tag(sync=True)

    # selected_viewer for spatial-spatial image.
    # NOTE: this is currently cubeviz-specific so will need to be updated
    # to be config-specific if using within other viewer configurations.
    viewer_to_id = {'Left': 'cubeviz-0', 'Center': 'cubeviz-1', 'Right': 'cubeviz-2'}
    viewers = List(['None', 'Left', 'Center', 'Right']).tag(sync=True)
    selected_viewer = Unicode('None').tag(sync=True)

    spectral_unit = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hub.subscribe(self, DataCollectionAddMessage,
                           handler=self._on_data_updated)
        self.hub.subscribe(self, DataCollectionDeleteMessage,
                           handler=self._on_data_updated)

        self._selected_data = None
        self._selected_cube = None
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
        data_label = event['new']
        if data_label not in self.data_collection.labels:
            return
        self._selected_data = self.data_collection[self.data_collection.labels.index(data_label)]
        self._selected_cube = self._selected_data.get_object(cls=Spectrum1D, statistic=None)
        self.spectral_unit = self._selected_cube.spectral_axis.unit.to_string()

    def vue_collapse(self, *args, **kwargs):
        # Collapsing over the spectral axis. Cut out the desired spectral
        # region. Defaults to the entire spectrum.
        spec_min = float(self.spectral_subset.selected_min(self._selected_cube)) * u.Unit(self.spectral_unit) # noqa
        spec_max = float(self.spectral_subset.selected_max(self._selected_cube)) * u.Unit(self.spectral_unit) # noqa

        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', message='No observer defined on WCS')
            spec = spectral_slab(self._selected_cube, spec_min, spec_max)
            # Spatial-spatial image only.
            collapsed_spec = spec.collapse(self.selected_func.lower(), axis=-1).T  # Quantity

        data = Data()
        data['flux'] = collapsed_spec.value
        data.get_component('flux').units = str(collapsed_spec.unit)

        self._label_counter += 1
        label = f"Collapsed {self._label_counter} {self._selected_data.label}"

        data.meta["Plugin"] = "Collapse"
        self.app.add_data(data, label)

        self._link_collapse_data()

        snackbar_message = SnackbarMessage(
            f"Data set '{self._selected_data.label}' collapsed successfully.",
            color="success",
            sender=self)
        self.hub.broadcast(snackbar_message)

        # Spatial-spatial image only.
        if self.selected_viewer != 'None':
            # replace the contents in the selected viewer with the results from this plugin
            self.app.add_data_to_viewer(self.viewer_to_id.get(self.selected_viewer),
                                        label, clear_other_data=True)

    def _link_collapse_data(self):
        """
        Link the new dataset pixel-wise to the original dataset. In general
        direct pixel to pixel links are the most efficient and should be
        used in cases like this where we know there is a 1-to-1 mapping of
        pixel coordinates.

        """
        new_len = len(self.app.data_collection)

        pc_new = self.app.data_collection[-1].pixel_component_ids

        # Link to the first dataset with compatible coordinates
        for i in range(new_len - 1):
            pc_old = self.app.data_collection[i].pixel_component_ids
            # If data_collection[i] is also from the collapse plugin
            if ("Plugin" in self.app.data_collection[i].meta and
                    self.app.data_collection[i].meta["Plugin"] == "Collapse"):
                links = [LinkSame(pc_old[0], pc_new[0]),
                         LinkSame(pc_old[1], pc_new[1])]

            # Else, link collapse data to cube (pc_old)
            else:
                links = [[LinkSame(pc_new[1], pc_old[2]),
                          LinkSame(pc_new[0], pc_old[1])]]

            self.app.data_collection.add_link(links)

            break
