import numpy as np

from astropy.convolution import convolve, Gaussian2DKernel
from specutils import Spectrum
from specutils.manipulation import gaussian_smooth
from traitlets import List, Unicode, Bool, observe

from jdaviz.core.custom_traitlets import FloatHandleEmpty
from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin, DatasetSelectMixin,
                                        SelectPluginComponent, AddResultsMixin,
                                        with_spinner)
from jdaviz.core.user_api import PluginUserApi

__all__ = ['GaussianSmooth']


@tray_registry('g-gaussian-smooth', label="Gaussian Smooth", category="data:manipulation")
class GaussianSmooth(PluginTemplateMixin, DatasetSelectMixin, AddResultsMixin):
    """
    See the :ref:`Gaussian Smooth Plugin Documentation <gaussian-smooth>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.close_in_tray`
    * ``dataset`` (:class:`~jdaviz.core.template_mixin.DatasetSelect`):
      Dataset to use for computing line statistics.
    * ``mode`` (:class:`~jdaviz.core.template_mixin.SelectPluginComponent`):
      Only available for Cubeviz.  Whether to use spatial or spectral smoothing.
    * :attr:`stddev`:
      Standard deviation of the gaussian to use for smoothing.
    * ``add_results`` (:class:`~jdaviz.core.template_mixin.AddResults`)
    * :meth:`smooth`
    """
    template_file = __file__, "gaussian_smooth.vue"
    stddev = FloatHandleEmpty(1).tag(sync=True)
    show_modes = Bool(False).tag(sync=True)
    mode_items = List().tag(sync=True)
    mode_selected = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.config == "cubeviz":
            self.docs_description = 'Smooth data cube spatially or spectrally with a Gaussian kernel.'  # noqa
            self.show_modes = True
            self.dataset._viewers = [
                self._default_flux_viewer_reference_name,
                self._default_spectrum_viewer_reference_name
            ]
            # clear the cache in case the spectrum-viewer selection was already cached
            self.dataset._clear_cache()
        elif self.config in ("mosviz", "specviz2d"):
            # only allow smoothing 1d spectra
            self.dataset._viewers = [self._default_spectrum_viewer_reference_name]
            self.dataset._clear_cache()

        self.dataset.add_filter('not_from_this_plugin', 'is_spectrum_or_cube')

        self.mode = SelectPluginComponent(self,
                                          items='mode_items',
                                          selected='mode_selected',
                                          manual_options=['Spectral', 'Spatial'])

        # set the filter on the dataset and viewer options
        self._update_dataset_viewer_filters()

        # description displayed under plugin title in tray
        self._plugin_description = 'Smooth data with a Gaussian kernel.'

        if self.app.config == 'deconfigged':
            self.observe_traitlets_for_relevancy(traitlets_to_observe=['dataset_items'])

    @property
    def _default_spectrum_viewer_reference_name(self):
        return getattr(
            self.app._jdaviz_helper, '_default_spectrum_viewer_reference_name', 'spectrum-viewer'
        )

    @property
    def _default_flux_viewer_reference_name(self):
        return getattr(
            self.app._jdaviz_helper, '_default_flux_viewer_reference_name', 'flux-viewer'
        )

    @property
    def user_api(self):
        expose = ['dataset', 'stddev', 'add_results', 'smooth']
        if self.config == "cubeviz":
            expose += ['mode']
        return PluginUserApi(self, expose=expose)

    @observe("dataset_selected", "stddev", "mode_selected")
    def _set_default_results_label(self, event={}):
        '''Generate a label and set the results field to that value'''
        if (hasattr(self, 'dataset') and (len(self.dataset.labels) >= 1) or self.app.config == 'mosviz'):  # noqa
            dataset = f'{self.dataset_selected} '
        else:
            # This should only happen at initialization. Will be overwritten with above
            # once data is loaded
            dataset = ''

        smooth_type = (f"{self.mode_selected.lower()}-smooth" if self.config == "cubeviz"
                       else "smooth")
        stddev = f"stddev-{self.stddev}"

        # Overriding is allowed, so do not check for uniqueness
        self.results_label_default = (
            self.app.return_data_label(f"{dataset}{smooth_type} {stddev}", check_unique=False))

    @observe("dataset_selected")
    def _update_viewer_filters(self, event={}):
        if not hasattr(self, 'dataset'):
            # during initial init, this can trigger before the component is initialized
            return

        if self.dataset.selected_dc_item is not None:
            selected_data_is_1d = len(self.dataset.selected_dc_item.data.shape) == 1

            if selected_data_is_1d:
                # only want spectral viewers in the options
                self.add_results.viewer.filters = ['is_spectrum_viewer']
            else:
                # only want image viewers in the options
                self.add_results.viewer.filters = ['is_image_viewer']

    @observe("mode_selected")
    def _update_dataset_viewer_filters(self, event={}):
        if event.get('new', self.mode_selected) == 'Spatial':
            # MUST be a cube
            self.dataset.add_filter('layer_in_flux_viewer')
        else:
            # can either be a cube OR a spectrum
            self.dataset.remove_filter('layer_in_flux_viewer')
        self._update_viewer_filters()

    def vue_apply(self, event={}):
        self.smooth(add_data=True)

    def smooth(self, add_data=True):
        """
        Smooth according to the settings in the plugin.

        Parameters
        ----------
        add_data : bool
            Whether to add the resulting trace to the application, according to the options
            defined in the plugin.

        Returns
        -------
        spec : `~specutils.Spectrum`
            The smoothed spectrum or data cube
        """
        if self.mode_selected == 'Spatial':
            if self.config != 'cubeviz':
                raise NotImplementedError("spatial smoothing only supported for Cubeviz")
            # TODO: in vuetify >2.3, timeout should be set to -1 to keep open
            #  indefinitely
            snackbar_message = SnackbarMessage(
                "Smoothing spatial slices of cube...",
                loading=True, timeout=0, sender=self)
            self.hub.broadcast(snackbar_message)

            results = self.spatial_smooth()

        else:
            results = self.spectral_smooth()

        if add_data:
            # add data to the collection/viewer
            self.add_results.add_results_from_plugin(results)
            self._set_default_results_label()

        snackbar_message = SnackbarMessage(
            f"Data set '{self.dataset_selected}' smoothed successfully.",
            color="success",
            sender=self)
        self.hub.broadcast(snackbar_message)

        return results

    @with_spinner()
    def spectral_smooth(self):
        """
        Smooth the input spectrum along the spectral axis.  To add the resulting spectrum into
        the app, set label options and use :meth:`smooth` instead.

        Returns
        -------
        spec : `~specutils.Spectrum`
            The smoothed spectrum
        """
        # Testing inputs to make sure putting smoothed spectrum into
        # datacollection works
        # input_flux = Quantity(np.array([0.2, 0.3, 2.2, 0.3]), u.Jy)
        # input_spaxis = Quantity(np.array([1, 2, 3, 4]), u.micron)
        # spec1 = Spectrum(input_flux, spectral_axis=input_spaxis)

        # Takes the user input from the dialog (stddev) and uses it to
        # define a standard deviation for gaussian smoothing
        cube = self.dataset.get_object(cls=Spectrum, statistic=None)
        spec_smoothed = gaussian_smooth(cube, stddev=self.stddev)

        return spec_smoothed

    @with_spinner('spinner')
    def spatial_smooth(self):
        """
        Use astropy convolution machinery to smooth the spatial dimensions of
        the data cube.  To add the resulting cube into
        the app, set label options and use :meth:`smooth` instead.

        Returns
        -------
        cube : `~specutils.Spectrum`
            The smoothed cube
        """
        cube = self.dataset.selected_obj
        flux_unit = cube.flux.unit

        # Extend the 2D kernel to have a length 1 spectral dimension, so that
        # we can do "3d" convolution to the whole cube
        kernel = np.expand_dims(Gaussian2DKernel(self.stddev), cube.meta['spectral_axis_index'])

        convolved_data = convolve(cube, kernel)

        # Copy 3D WCS from input cube.
        data = self.dataset.selected_dc_item
        # Similar to coords_info logic.
        if '_orig_spec' in getattr(data, 'meta', {}):
            w = data.meta['_orig_spec'].wcs
        else:
            w = data.coords

        # Create a new cube with the old metadata. Note that astropy
        # convolution generates values for masked (NaN) data.
        newcube = Spectrum(flux=convolved_data * flux_unit, wcs=w)

        return newcube
