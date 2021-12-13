import numpy as np

from astropy import units as u
from astropy.convolution import convolve, Gaussian2DKernel
from glue.core.message import (DataCollectionAddMessage,
                               DataCollectionDeleteMessage)
from specutils import Spectrum1D
from specutils.manipulation import gaussian_smooth
from traitlets import List, Unicode, Any, Bool, observe

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin

__all__ = ['GaussianSmooth']


spaxel = u.def_unit('spaxel', 1 * u.Unit(""))
u.add_enabled_units([spaxel])


@tray_registry('g-gaussian-smooth', label="Gaussian Smooth")
class GaussianSmooth(TemplateMixin):
    template_file = __file__, "gaussian_smooth.vue"
    stddev = Any().tag(sync=True)
    dc_items = List([]).tag(sync=True)
    selected_data = Unicode().tag(sync=True)
    selected_data_is_1d = Bool(True).tag(sync=True)
    show_modes = Bool(False).tag(sync=True)
    smooth_modes = List(["Spectral", "Spatial"]).tag(sync=True)
    selected_mode = Unicode("Spectral").tag(sync=True)

    # add/replace is used for spectral (add for 1D, replace for 2D)
    add_replace_results = Bool(True).tag(sync=True)

    # selected_viewer for spatial smoothing
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
        if self.config == "cubeviz":
            self.show_modes = True

    def _on_data_updated(self, msg):
        self.dc_items = [x.label for x in self.data_collection]

    @observe("selected_data")
    def _on_data_selected(self, event):
        self._selected_data = next((x for x in self.data_collection
                                    if x.label == event['new']))
        self.selected_data_is_1d = len(self._selected_data.data.shape) == 1

    def vue_spectral_smooth(self, *args, **kwargs):
        # Testing inputs to make sure putting smoothed spectrum into
        # datacollection works
        # input_flux = Quantity(np.array([0.2, 0.3, 2.2, 0.3]), u.Jy)
        # input_spaxis = Quantity(np.array([1, 2, 3, 4]), u.micron)
        # spec1 = Spectrum1D(input_flux, spectral_axis=input_spaxis)
        size = float(self.stddev)

        try:
            spec = self._selected_data.get_object(cls=Spectrum1D, statistic=None)
        except TypeError:
            snackbar_message = SnackbarMessage(
                "Unable to perform smoothing over selected data.",
                color="error",
                sender=self)
            self.hub.broadcast(snackbar_message)

            return

        # Takes the user input from the dialog (stddev) and uses it to
        # define a standard deviation for gaussian smoothing
        spec_smoothed = gaussian_smooth(spec, stddev=size)

        label = f"Smoothed {self._selected_data.label} stddev {size}"

        if label in self.data_collection:
            snackbar_message = SnackbarMessage(
                "Data with selected stddev already exists, canceling operation.",
                color="error",
                sender=self)
            self.hub.broadcast(snackbar_message)

            return

        # add data to the collection
        self.app.add_data(spec_smoothed, label)
        if self.add_replace_results:
            viewer = "spectrum-viewer" if self.selected_data_is_1d or self.app.config == 'cubeviz' else "spectrum-2d-viewer" # noqa
            self.app.add_data_to_viewer(viewer, label,
                                        clear_other_data=viewer != "spectrum-viewer")

        if not self.selected_data_is_1d and self.selected_viewer != 'None':
            # replace the contents in the selected viewer with the smoothed cube
            self.app.add_data_to_viewer(self.viewer_to_id.get(self.selected_viewer),
                                        label, clear_other_data=True)

        snackbar_message = SnackbarMessage(
            f"Data set '{self._selected_data.label}' smoothed successfully.",
            color="success",
            sender=self)
        self.hub.broadcast(snackbar_message)

    def vue_spatial_convolution(self, *args):
        """
        Use astropy convolution machinery to smooth the spatial dimensions of
        the data cube.
        """

        size = float(self.stddev)

        label = f"Smoothed {self._selected_data.label} spatial stddev {size}"

        if label in self.data_collection:
            # immediately cancel before smoothing
            snackbar_message = SnackbarMessage(
                "Data with selected stddev already exists, canceling operation.",
                color="error",
                sender=self)
            self.hub.broadcast(snackbar_message)

            return

        # Get information from the flux component
        attribute = self._selected_data.main_components[0]

        cube = self._selected_data.get_object(cls=Spectrum1D,
                                              attribute=attribute,
                                              statistic=None)
        flux_unit = cube.flux.unit

        # Extend the 2D kernel to have a length 1 spectral dimension, so that
        # we can do "3d" convolution to the whole cube
        kernel = np.expand_dims(Gaussian2DKernel(size), 2)

        # TODO: in vuetify >2.3, timeout should be set to -1 to keep open
        #  indefinitely
        snackbar_message = SnackbarMessage(
            "Smoothing spatial slices of cube...",
            loading=True, timeout=0, sender=self)
        self.hub.broadcast(snackbar_message)

        convolved_data = convolve(cube, kernel)

        # Create a new cube with the old metadata. Note that astropy
        # convolution generates values for masked (NaN) data.
        newcube = Spectrum1D(flux=convolved_data * flux_unit, wcs=cube.wcs)

        # add data to the collection
        self.app.add_data(newcube, label)
        if self.selected_viewer != 'None':
            # replace the contents in the selected viewer with the results from this plugin
            self.app.add_data_to_viewer(self.viewer_to_id.get(self.selected_viewer),
                                        label, clear_other_data=True)

        snackbar_message = SnackbarMessage(
            f"Data set '{self._selected_data.label}' smoothed successfully.",
            color="success",
            sender=self)
        self.hub.broadcast(snackbar_message)
