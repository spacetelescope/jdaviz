import os

from astropy import units as u
from astropy.nddata import CCDData
from glue.core.message import (DataCollectionAddMessage,
                               DataCollectionDeleteMessage)
from glue.core.link_helpers import LinkSame

from traitlets import List, Unicode, Any, Bool, observe
from specutils import Spectrum1D, manipulation, analysis

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, SpectralSubsetSelectMixin

__all__ = ['MomentMap']


spaxel = u.def_unit('spaxel', 1 * u.Unit(""))
u.add_enabled_units([spaxel])


@tray_registry('cubeviz-moment-maps', label="Moment Maps")
class MomentMap(PluginTemplateMixin, SpectralSubsetSelectMixin):
    template_file = __file__, "moment_maps.vue"
    n_moment = Any().tag(sync=True)
    dc_items = List([]).tag(sync=True)
    selected_data = Unicode().tag(sync=True)

    filename = Unicode().tag(sync=True)

    moment_available = Bool(False).tag(sync=True)
    spectral_unit = Unicode().tag(sync=True)

    # NOTE: this is currently cubeviz-specific so will need to be updated
    # to be config-specific if using within other viewer configurations.
    viewer_to_id = {'Left': 'cubeviz-0', 'Center': 'cubeviz-1', 'Right': 'cubeviz-2'}
    viewers = List(['None', 'Left', 'Center', 'Right']).tag(sync=True)
    selected_viewer = Unicode('None').tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hub.subscribe(self, DataCollectionAddMessage,
                           handler=self._on_data_updated)
        self.hub.subscribe(self, DataCollectionDeleteMessage,
                           handler=self._on_data_updated)

        self._selected_data = None
        self.n_moment = 0
        self.moment = None

    def _on_data_updated(self, msg):
        self.dc_items = [x.label for x in self.data_collection]
        # Default to selecting the first loaded cube
        if self._selected_data is None:
            for i in range(len(self.dc_items)):
                # Also set the spectral min and max to default to the full range
                try:
                    self.selected_data = self.dc_items[i]
                    cube = self._selected_data.get_object(cls=Spectrum1D, statistic=None)
                    self.spectral_unit = str(cube.spectral_axis.unit)
                    break
                # Skip data that can't be returned as a Spectrum1D
                except (ValueError, TypeError):
                    continue

    @observe("selected_data")
    def _on_data_selected(self, event):
        self._selected_data = next((x for x in self.data_collection
                                    if x.label == event['new']))
        cube = self._selected_data.get_object(cls=Spectrum1D, statistic=None)
        # Update spectral bounds and unit if we've switched to another unit
        if str(cube.spectral_axis.unit) != self.spectral_unit:
            self.spectral_unit = str(cube.spectral_axis.unit)

    def vue_calculate_moment(self, *args):
        # Retrieve the data cube and slice out desired region, if specified
        cube = self._selected_data.get_object(cls=Spectrum1D, statistic=None)
        spec_min = float(self.spectral_subset.selected_min(cube)) * u.Unit(self.spectral_unit)
        spec_max = float(self.spectral_subset.selected_max(cube)) * u.Unit(self.spectral_unit)
        slab = manipulation.spectral_slab(cube, spec_min, spec_max)

        # Calculate the moment and convert to CCDData to add to the viewers
        try:
            n_moment = int(self.n_moment)
            if n_moment < 0:
                raise ValueError("Moment must be a positive integer")
        except ValueError:
            raise ValueError("Moment must be a positive integer")
        # Need transpose to align JWST mirror shape. Not sure why.
        self.moment = CCDData(analysis.moment(slab, order=n_moment).T)

        label = "Moment {}: {}".format(n_moment, self._selected_data.label)
        fname_label = self._selected_data.label.replace("[", "_").replace("]", "")
        self.filename = "moment{}_{}.fits".format(n_moment, fname_label)

        # Add information to meta data that this originated from
        # the moment map plugin. Then, link the moment map data
        # to the existing data in data_collection
        self.moment.meta["Plugin"] = "Moment Map"
        self.app.add_data(self.moment, label)
        self._link_moment_data()

        self.moment_available = True

        msg = SnackbarMessage("{} added to data collection".format(label),
                              sender=self, color="success")
        self.hub.broadcast(msg)

        if self.selected_viewer != 'None':
            # replace the contents in the selected viewer with the results from this plugin
            self.app.add_data_to_viewer(self.viewer_to_id.get(self.selected_viewer),
                                        label, clear_other_data=True)

    def vue_save_as_fits(self, *args):
        if self.moment is None or not self.filename:  # pragma: no cover
            return

        self.moment.write(self.filename)
        # Let the user know where we saved the file.
        self.hub.broadcast(SnackbarMessage(
            f"Moment map saved to {os.path.abspath(self.filename)}", sender=self, color="success"))

    def _link_moment_data(self):
        new_len = len(self.app.data_collection)

        # Can't link if there's no world_component_ids
        pc_new = self.app.data_collection[-1].pixel_component_ids

        # Link to the first dataset with compatible coordinates
        for i in range(new_len - 1):
            pc_old = self.app.data_collection[i].pixel_component_ids
            # If data_collection[i] is also from the moment map
            if ("Plugin" in self.app.data_collection[i].meta and
                    self.app.data_collection[i].meta["Plugin"] == "Moment Map"):
                links = [LinkSame(pc_old[0], pc_new[0]),
                         LinkSame(pc_old[1], pc_new[1])]

            # Link moment map to cube (pc_old)
            else:
                links = [LinkSame(pc_old[1], pc_new[0]),
                         LinkSame(pc_old[2], pc_new[1])]

            self.app.data_collection.add_link(links)

            break
