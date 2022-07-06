import numpy as np

from astropy import units as u
from astropy.convolution import convolve, Gaussian2DKernel
from specutils import Spectrum1D
from specutils.manipulation import gaussian_smooth
from traitlets import List, Unicode, Bool, observe

from jdaviz.core.custom_traitlets import FloatHandleEmpty
from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin, DatasetSelectMixin, AddResultsMixin

__all__ = ['GaussianSmooth']


spaxel = u.def_unit('spaxel', 1 * u.Unit(""))
u.add_enabled_units([spaxel])


@tray_registry('g-gaussian-smooth', label="Gaussian Smooth")
class GaussianSmooth(TemplateMixin, DatasetSelectMixin, AddResultsMixin):
    template_file = __file__, "gaussian_smooth.vue"
    stddev = FloatHandleEmpty(1).tag(sync=True)
    selected_data_is_1d = Bool(True).tag(sync=True)
    show_modes = Bool(False).tag(sync=True)
    smooth_modes = List(["Spectral", "Spatial"]).tag(sync=True)
    selected_mode = Unicode("Spectral").tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.config == "cubeviz":
            self.show_modes = True
            # retrieve the data from the cube, not the collapsed 1d spectrum
            self.dataset._viewers = ['flux-viewer', 'spectrum-viewer']
            # clear the cache in case the spectrum-viewer selection was already cached
            self.dataset._clear_cache()
        elif self.config == "mosviz":
            # only allow smoothing 1d spectra
            self.dataset._viewers = ['spectrum-viewer']
            self.dataset._clear_cache()

        # set the filter on the viewer options
        self._update_viewer_filters()

    @observe("dataset_selected", "dataset_items", "stddev", "selected_mode")
    def _set_default_results_label(self, event={}):
        label_comps = []
        if hasattr(self, 'dataset') and (len(self.dataset.labels) > 1 or self.app.config == 'mosviz'):  # noqa
            label_comps += [self.dataset_selected]
        if self.config == "cubeviz":
            label_comps += [f"{self.selected_mode.lower()}-smooth"]
        else:
            label_comps += ["smooth"]
        label_comps += [f"stddev-{self.stddev}"]
        self.results_label_default = " ".join(label_comps)

    @observe("dataset_selected")
    def _on_data_selected(self, event={}):
        if not hasattr(self, 'dataset'):
            # during initial init, this can trigger before the component is initialized
            return

        # NOTE: if this is ever used anywhere else, it should be moved into DatasetSelect
        if self.dataset.selected_dc_item is not None:
            self.selected_data_is_1d = len(self.dataset.selected_dc_item.data.shape) == 1

    @observe("selected_mode")
    def _update_viewer_filters(self, event={}):
        if event.get('new', self.selected_mode) == 'Spatial':
            # only want image viewers in the options
            self.add_results.viewer.filters = ['is_image_viewer']
        else:
            # only want spectral viewers in the options
            self.add_results.viewer.filters = ['is_spectrum_viewer']

    def vue_apply(self, event={}):
        if self.selected_mode == 'Spatial':
            self.apply_spatial_convolution()
        else:
            self.apply_spectral_smooth()

    def apply_spectral_smooth(self):
        # Testing inputs to make sure putting smoothed spectrum into
        # datacollection works
        # input_flux = Quantity(np.array([0.2, 0.3, 2.2, 0.3]), u.Jy)
        # input_spaxis = Quantity(np.array([1, 2, 3, 4]), u.micron)
        # spec1 = Spectrum1D(input_flux, spectral_axis=input_spaxis)

        # Takes the user input from the dialog (stddev) and uses it to
        # define a standard deviation for gaussian smoothing
        cube = self.dataset.get_object(cls=Spectrum1D, statistic=None)
        spec_smoothed = gaussian_smooth(cube, stddev=self.stddev)

        # add data to the collection/viewer
        self.add_results.add_results_from_plugin(spec_smoothed)

        snackbar_message = SnackbarMessage(
            f"Data set '{self.dataset_selected}' smoothed successfully.",
            color="success",
            sender=self)
        self.hub.broadcast(snackbar_message)

    def apply_spatial_convolution(self):
        """
        Use astropy convolution machinery to smooth the spatial dimensions of
        the data cube.
        """
        if self.results_label in self.data_collection:
            # immediately cancel before smoothing
            snackbar_message = SnackbarMessage(
                "Data with selected stddev already exists, canceling operation.",
                color="error",
                sender=self)
            self.hub.broadcast(snackbar_message)

            return

        # Get information from the flux component
        attribute = self.dataset.selected_dc_item.main_components[0]

        cube = self.dataset.get_object(cls=Spectrum1D,
                                       attribute=attribute,
                                       statistic=None)
        flux_unit = cube.flux.unit

        # Extend the 2D kernel to have a length 1 spectral dimension, so that
        # we can do "3d" convolution to the whole cube
        kernel = np.expand_dims(Gaussian2DKernel(self.stddev), 2)

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

        # add data to the collection/plots
        self.add_results.add_results_from_plugin(newcube)
        self._set_default_results_label()

        snackbar_message = SnackbarMessage(
            f"Data set '{self.dataset_selected}' smoothed successfully.",
            color="success",
            sender=self)
        self.hub.broadcast(snackbar_message)
