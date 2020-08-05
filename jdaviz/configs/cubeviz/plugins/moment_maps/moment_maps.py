from astropy import units as u
from glue.core.message import (DataCollectionAddMessage,
                               DataCollectionDeleteMessage)
from traitlets import List, Unicode, Int, observe
from spectral_cube import SpectralCube

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template

__all__ = ['MomentMaps']


spaxel = u.def_unit('spaxel', 1 * u.Unit(""))
u.add_enabled_units([spaxel])


@tray_registry('cubeviz-moment-maps', label="Moment Maps")
class GaussianSmooth(TemplateMixin):
    template = load_template("moment_maps.vue", __file__).tag(sync=True)
    n_moment = Int().tag(sync=True)
    dc_items = List([]).tag(sync=True)
    subsets = List([]).tag(sync=True)
    selected_data = Unicode().tag(sync=True)
    selected_spectral_subset = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hub.subscribe(self, DataCollectionAddMessage,
                           handler=self._on_data_updated)
        self.hub.subscribe(self, DataCollectionDeleteMessage,
                           handler=self._on_data_updated)

        self._selected_data = None
        self.n_moment = 0
        self.moment = None
        self.spectral_min = None
        self.spectral_max = None

    def _on_subsets_updates(self, msg):
        pass

    def _on_data_updated(self, msg):
        self.dc_items = [x.label for x in self.data_collection]

    @observe("selected_data")
    def _on_data_selected(self, event):
        self._selected_data = next((x for x in self.data_collection
                                    if x.label == event['new']))

    def vue_calculate_moments(self):
        # Retrieve the data cube and slice out desired region, if specified
        cube = self._selected_data.get_object(cls=SpectralCube)
        spec_min = self.spectral_min or cube.spectral_axis[0]
        spec_max = self.spectral_max or cube.spectral_axis[-1]
        slab = cube.spectral_slab(spec_min, spec_max)
        self.moment = slab.moment(self.n_moment)

