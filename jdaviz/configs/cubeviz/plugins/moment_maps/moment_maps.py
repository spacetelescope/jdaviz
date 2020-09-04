import os
import pathlib
import re

from astropy import units as u
from astropy.nddata import CCDData
from glue.core.message import (DataCollectionAddMessage,
                               DataCollectionDeleteMessage,
                               SubsetCreateMessage)
from traitlets import List, Unicode, Int, Any, Bool, observe
from spectral_cube import SpectralCube
from specutils import SpectralRegion
from regions import RectanglePixelRegion

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template

__all__ = ['MomentMap']


spaxel = u.def_unit('spaxel', 1 * u.Unit(""))
u.add_enabled_units([spaxel])


@tray_registry('cubeviz-moment-maps', label="Moment Maps")
class MomentMap(TemplateMixin):
    template = load_template("moment_maps.vue", __file__).tag(sync=True)
    n_moment = Any().tag(sync=True)
    dc_items = List([]).tag(sync=True)
    selected_data = Unicode().tag(sync=True)

    filename = Unicode().tag(sync=True)

    moment_available = Bool(False).tag(sync=True)
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
        #self.hub.subscribe(self, SubsetCreateMessage,
        #                   handler=self._on_subset_created)
        self._selected_data = None
        self.n_moment = 0
        self.moment = None
        self._filename = None
        self.spectral_min = 0.0
        self.spectral_max = 0.0
        self._spectral_subsets = {}

    def _on_data_updated(self, msg):
        self.dc_items = [x.label for x in self.data_collection]
        # Default to selecting the first loaded cube
        if self._selected_data is None:
            for i in range(len(self.dc_items)):
                # Also set the spectral min and max to default to the full range
                try:
                    self.selected_data = self.dc_items[i]
                    cube = self._selected_data.get_object(cls=SpectralCube)
                    self.spectral_min = cube.spectral_axis[0].value
                    self.spectral_max = cube.spectral_axis[-1].value
                    self.spectral_unit = str(cube.spectral_axis.unit)
                    break
                # Skip data that can't be returned as a SpectralCube
                except (ValueError, TypeError):
                    continue

    def _on_subset_created(self, msg):
        """Currently unimplemented due to problems with the SubsetCreateMessafe"""
        raise ValueError(msg)

    @observe("selected_data")
    def _on_data_selected(self, event):
        self._selected_data = next((x for x in self.data_collection
                                    if x.label == event['new']))
        cube = self._selected_data.get_object(cls=SpectralCube)
        # Update spectral bounds and unit if we've switched to another unit
        if str(cube.spectral_axis.unit) != self.spectral_unit:
            self.spectral_min = cube.spectral_axis[0].value
            self.spectral_max = cube.spectral_axis[-1].value
            self.spectral_unit = str(cube.spectral_axis.unit)

    @observe("selected_subset")
    def _on_subset_selected(self, event):
        # If "None" selected, reset based on bounds of selected data
        self._selected_subset = self.selected_subset
        if self._selected_subset == "None":
            cube = self._selected_data.get_object(cls=SpectralCube)
            self.spectral_min = cube.spectral_axis[0].value
            self.spectral_max = cube.spectral_axis[-1].value
        else:
            spec_sub = self._spectral_subsets[self._selected_subset]
            unit = u.Unit(self.spectral_unit)
            spec_reg = SpectralRegion.from_center(spec_sub.center.x * unit,
                                                  spec_sub.width * unit)
            self.spectral_min = spec_reg.lower.value
            self.spectral_max = spec_reg.upper.value

    @observe("filename")
    def _on_filename_changed(self, event):
        self._filename = self.filename

    def vue_list_subsets(self, event):
        """Populate the spectral subset selection dropdown"""
        temp_subsets = self.app.get_subsets_from_viewer("spectrum-viewer")
        temp_list = ["None"]
        temp_dict = {}
        # Attempt to filter out spatial subsets
        for key, region in temp_subsets.items():
            if type(region) == RectanglePixelRegion:
                temp_dict[key] = region
                temp_list.append(key)
        self._spectral_subsets = temp_dict
        self.spectral_subset_items = temp_list

    def vue_calculate_moment(self, event):
        #Retrieve the data cube and slice out desired region, if specified
        cube = self._selected_data.get_object(cls=SpectralCube)
        spec_min = float(self.spectral_min) * u.Unit(self.spectral_unit)
        spec_max = float(self.spectral_max) * u.Unit(self.spectral_unit)
        slab = cube.spectral_slab(spec_min, spec_max)

        # Calculate the moment and convert to CCDData to add to the viewers
        try:
            n_moment = int(self.n_moment)
            if n_moment < 0:
                raise ValueError("Moment must be a positive integer")
        except ValueError:
            raise ValueError("Moment must be a positive integer")
        self.moment = slab.moment(n_moment)

        moment_ccd = CCDData(self.moment.array, wcs=self.moment.wcs,
                             unit=self.moment.unit)

        label = "Moment {}: {}".format(n_moment, self._selected_data.label)
        fname_label = self._selected_data.label.replace("[", "_").replace("]", "_")
        self.filename = "moment{}_{}.fits".format(n_moment, fname_label)
        self.data_collection[label] = moment_ccd
        self.moment_available = True

        msg = SnackbarMessage("{} added to data collection".format(label),
                              sender=self, color="success")
        self.hub.broadcast(msg)

    def vue_save_as_fits(self, event):
        self.moment.write(self._filename)
        # Let the user know where we saved the file (don't need path if user
        # specified a full filepath
        if re.search("/", self._filename) is None:
            wd = pathlib.Path.cwd()
            full_path = wd / pathlib.Path(self._filename)
        else:
            full_path = self._filename
        msg = SnackbarMessage("Moment map saved to {}".format(str(full_path)),
                              sender=self, color="success")
        self.hub.broadcast(msg)
