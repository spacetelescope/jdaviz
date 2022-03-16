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

        self.data_collection[label] = data

        # Link the new dataset pixel-wise to the original dataset. In general
        # direct pixel to pixel links are the most efficient and should be
        # used in cases like this where we know there is a 1-to-1 mapping of
        # pixel coordinates.
        # Spatial-spatial image only.
        pix_id_1 = self._selected_data.pixel_component_ids[0]  # Pixel Axis 0 [z]
        pix_id_1c = self.data_collection[label].pixel_component_ids[0]  # Pixel Axis 0 [y]
        pix_id_2 = self._selected_data.pixel_component_ids[1]  # Pixel Axis 1 [y]
        pix_id_2c = self.data_collection[label].pixel_component_ids[1]  # Pixel Axis 1 [x]

        self.data_collection.add_link([LinkSame(pix_id_1, pix_id_1c),
                                       LinkSame(pix_id_2, pix_id_2c)])

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
