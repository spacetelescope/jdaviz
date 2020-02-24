from astropy import units as u
from astropy import units as u
from glue.core.message import (DataCollectionAddMessage,
                               DataCollectionDeleteMessage)
from specutils import Spectrum1D
from specutils.manipulation import gaussian_smooth
from traitlets import Bool, List, Unicode

from jdaviz.core.registries import tools
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template

__all__ = ['LineFlux']


spaxel = u.def_unit('spaxel', 1 * u.Unit(""))
u.add_enabled_units([spaxel])


@tools('g-line-flux')
class LineFlux(TemplateMixin):
    dialog = Bool(False).tag(sync=True)
    template = load_template("line_flux.vue", __file__).tag(sync=True)
    stddev = Unicode().tag(sync=True)
    dc_items = List([]).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hub.subscribe(self, DataCollectionAddMessage,
                           handler=self._on_data_updated)
        self.hub.subscribe(self, DataCollectionDeleteMessage,
                           handler=self._on_data_updated)

        self._selected_data = None

    def _on_data_updated(self, msg):
        self.dc_items = [x.label for x in self.data_collection]

    def vue_data_selected(self, event):
        self._selected_data = next((x for x in self.data_collection
                                    if x.label == event))

    def vue_line_flux(self, *args, **kwargs):
        # Testing inputs to make sure putting smoothed spectrum into
        # datacollection works
        # input_flux = Quantity(np.array([0.2, 0.3, 2.2, 0.3]), u.Jy)
        # input_spaxis = Quantity(np.array([1, 2, 3, 4]), u.micron)
        # spec1 = Spectrum1D(input_flux, spectral_axis=input_spaxis)
        size = float(self.stddev)
        spec = self._selected_data.get_object(cls=Spectrum1D)

        # Takes the user input from the dialog (stddev) and uses it to
        # define a standard deviation for gaussian smoothing
        spec_smoothed = gaussian_smooth(spec, stddev=size)

        self.data_collection[f"Smoothed {self._selected_data.label}"] = spec_smoothed

        self.dialog = False
