from astropy import units as u
from glue.core.message import (DataCollectionAddMessage,
                               DataCollectionDeleteMessage)
from specutils import Spectrum1D
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
    wavelength = Unicode().tag(sync=True)
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
        input_wavelength = int(self.wavelength)
        spec = self._selected_data.get_object(cls=Spectrum1D)

        # Takes the user input from the dialog (wavelength) and
        # finds the flux at that input

        print(spec.flux[input_wavelength])
        self.dialog = False
