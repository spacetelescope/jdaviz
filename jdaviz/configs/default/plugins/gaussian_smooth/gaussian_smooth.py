from astropy import units as u
from astropy import units as u
from glue.core.message import (DataCollectionAddMessage,
                               DataCollectionDeleteMessage)
from glue.core.link_helpers import LinkSame
from specutils import Spectrum1D
from specutils.manipulation import gaussian_smooth
from traitlets import Bool, List, Unicode

from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template

__all__ = ['GaussianSmooth']


spaxel = u.def_unit('spaxel', 1 * u.Unit(""))
u.add_enabled_units([spaxel])


@tray_registry('g-gaussian-smooth', label="Gaussian Smooth")
class GaussianSmooth(TemplateMixin):
    dialog = Bool(False).tag(sync=True)
    template = load_template("gaussian_smooth.vue", __file__).tag(sync=True)
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

    def vue_gaussian_smooth(self, *args, **kwargs):
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

        label = f"Smoothed {self._selected_data.label}"

        self.data_collection[label] = spec_smoothed

        # Link the new dataset pixel-wise to the original dataset. In general
        # direct pixel to pixel links are the most efficient and should be
        # used in cases like this where we know there is a 1-to-1 mapping of
        # pixel coordinates. Here the smoothing returns a 1-d spectral object
        # which we can link to the first dimension of the original dataset
        # (whcih could in principle be a cube or a spectrum)
        self.data_collection.add_link(LinkSame(self._selected_data.pixel_component_ids[0],
                                               self.data_collection[label].pixel_component_ids[0]))

        self.dialog = False
