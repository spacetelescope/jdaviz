from astropy import units as u
from astropy.nddata import CCDData
from glue.core.message import (DataCollectionAddMessage,
                               DataCollectionDeleteMessage,
                               SubsetCreateMessage)
from traitlets import List, Unicode, Int, Float, Bool, observe
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
    n_moment = Int().tag(sync=True)
    dc_items = List([]).tag(sync=True)
    selected_data = Unicode().tag(sync=True)

    filename = Unicode().tag(sync=True)

    moment_available = Bool(False).tag(sync=True)
    spectral_min = Float().tag(sync=True)
    spectral_max = Float().tag(sync=True)
    spectral_unit = Unicode().tag(sync=True)
    spectral_subset_items = List([]).tag(sync=True)
    selected_subset = Unicode().tag(sync=True)

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
        self._selected_subset = None
        self.spectral_subset_items = []

    def _on_data_updated(self, msg):
        self.dc_items = [x.label for x in self.data_collection]
        # Default to selecting the first loaded data
        if self._selected_data is None:
            self.selected_data = self.dc_items[0]
            # Also set the spectral min and max to default to the full range
            cube = self._selected_data.get_object(cls=SpectralCube)
            self.spectral_min = cube.spectral_axis[0].value
            self.spectral_max = cube.spectral_axis[-1].value
            self.spectral_unit = str(cube.spectral_axis.unit)

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
        self._selected_subset = self.selected_subset
        spec_sub = self._spectral_subsets[self._selected_subset]
        unit = u.Unit(self.spectral_unit)
        spec_reg = SpectralRegion.from_center(spec_sub.center.x * unit,
                                              (spec_sub.width / 2) * unit)
        self.spectral_min = spec_reg.lower.value
        self.spectral_max = spec_reg.upper.value

    @observe("filename")
    def _on_filename_changed(self, event):
        self._filename = self.filename

    def vue_list_subsets(self, event):
         """Populate the spectral subset selection dropdown"""
         temp_subsets = self.app.get_subsets_from_viewer("spectrum-viewer")
         temp_list = []
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
        spec_min = self.spectral_min * u.Unit(self.spectral_unit)
        spec_max = self.spectral_max * u.Unit(self.spectral_unit)
        slab = cube.spectral_slab(spec_min, spec_max)

        # Calculate the moment and convert to CCDData to add to the viewers
        self.moment = slab.moment(self.n_moment)

        moment_ccd = CCDData(self.moment.array, wcs=self.moment.wcs,
                             unit=self.moment.unit)

        label = "Moment {}: {}".format(self.n_moment, self._selected_data.label)
        self.data_collection[label] = moment_ccd
        self.moment_available = True

    def vue_save_as_fits(self, event):
        self.moment.write(self._filename)
