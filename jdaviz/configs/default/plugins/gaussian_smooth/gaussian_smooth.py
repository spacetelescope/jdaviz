from astropy import units as u
from glue.core.message import (DataCollectionAddMessage,
                               DataCollectionDeleteMessage)
from specutils import Spectrum1D
from specutils.manipulation import gaussian_smooth
from traitlets import List, Unicode, Int, Any, observe

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template

__all__ = ['GaussianSmooth']


spaxel = u.def_unit('spaxel', 1 * u.Unit(""))
u.add_enabled_units([spaxel])


@tray_registry('g-gaussian-smooth', label="Gaussian Smooth")
class GaussianSmooth(TemplateMixin):
    template = load_template("gaussian_smooth.vue", __file__).tag(sync=True)
    stddev = Any().tag(sync=True)
    dc_items = List([]).tag(sync=True)
    selected_data = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hub.subscribe(self, DataCollectionAddMessage,
                           handler=self._on_data_updated)
        self.hub.subscribe(self, DataCollectionDeleteMessage,
                           handler=self._on_data_updated)

        self._selected_data = None

    def _on_data_updated(self, msg):
        self.dc_items = [x.label for x in self.data_collection]

    @observe("selected_data")
    def _on_data_selected(self, event):
        self._selected_data = next((x for x in self.data_collection
                                    if x.label == event['new']))

    def vue_gaussian_smooth(self, *args, **kwargs):
        # Testing inputs to make sure putting smoothed spectrum into
        # datacollection works
        # input_flux = Quantity(np.array([0.2, 0.3, 2.2, 0.3]), u.Jy)
        # input_spaxis = Quantity(np.array([1, 2, 3, 4]), u.micron)
        # spec1 = Spectrum1D(input_flux, spectral_axis=input_spaxis)
        size = float(self.stddev)

        try:
            spec = self._selected_data.get_object(cls=Spectrum1D)
        except TypeError:
            snackbar_message = SnackbarMessage(
                f"Unable to perform smoothing over selected data.",
                color="error",
                sender=self)
            self.hub.broadcast(snackbar_message)

            return

        # Takes the user input from the dialog (stddev) and uses it to
        # define a standard deviation for gaussian smoothing
        spec_smoothed = gaussian_smooth(spec, stddev=size)

        label = f"Smoothed {self._selected_data.label}"

        self.data_collection[label] = spec_smoothed

        snackbar_message = SnackbarMessage(
            f"Data set '{self._selected_data.label}' smoothed successfully.",
            color="success",
            sender=self)
        self.hub.broadcast(snackbar_message)
