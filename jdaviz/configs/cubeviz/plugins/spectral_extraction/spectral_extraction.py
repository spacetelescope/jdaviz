from functools import cached_property

import numpy as np
import astropy
from astropy import units as u
from astropy.nddata import NDDataArray, StdDevUncertainty
from traitlets import Any, Bool, Dict, Float, List, Unicode, observe

from jdaviz.core.custom_traitlets import FloatHandleEmpty
from jdaviz.core.events import SnackbarMessage, SliceValueUpdatedMessage, GlobalDisplayUnitChanged
from jdaviz.core.marks import PluginLine
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin,
                                        DatasetSelectMixin,
                                        SelectPluginComponent,
                                        ApertureSubsetSelectMixin,
                                        ApertureSubsetSelect,
                                        AddResults, AddResultsMixin,
                                        skip_if_not_tray_instance,
                                        skip_if_no_updates_since_last_active,
                                        with_spinner, with_temp_disable)
from jdaviz.core.user_api import PluginUserApi
from jdaviz.core.unit_conversion_utils import (all_flux_unit_conversion_equivs,
                                               flux_conversion_general,
                                               check_if_unit_is_per_solid_angle)
from jdaviz.configs.cubeviz.plugins.parsers import _return_spectrum_with_correct_units
from jdaviz.configs.cubeviz.plugins.viewers import WithSliceIndicator


__all__ = ['SpectralExtraction']


@tray_registry(
    'cubeviz-spectral-extraction', label="Spectral Extraction", viewer_requirements='spectrum'
)
class SpectralExtraction(PluginTemplateMixin, ApertureSubsetSelectMixin,
                         DatasetSelectMixin, AddResultsMixin):
    """
    See the :ref:`Spectral Extraction Plugin Documentation <spectral-extraction>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.close_in_tray`
    * ``aperture`` (:class:`~jdaviz.core.template_mixin.ApertureSubsetSelect`):
      Subset to use for the spectral extraction, or ``Entire Cube``.
    * ``wavelength_dependent``:
      Whether the ``aperture`` should be considered wavelength-dependent.  The cone is defined
      to intersect ``aperture`` at ``reference_spectral_value``.
    * ``reference_spectral_value``:
      The wavelength that will be used to calculate the radius of the cone through the cube.
    * ``background`` (:class:`~jdaviz.core.template_mixin.ApertureSubsetSelect`):
      Subset to use for background subtraction, or ``None``.
    * ``bg_wavelength_dependent``:
      Whether the ``background`` aperture should be considered wavelength-dependent (requires
      ``wavelength_dependent`` to also be set to ``True``). The cone is defined
      to intersect ``background`` at ``reference_spectral_value``.
    * ```bg_spec_per_spaxel``:
        Whether to normalize the background per spaxel when calling ``extract_bg_spectrum``.
        Otherwise, the spectrum will be scaled by the ratio between the
        areas of the aperture and the background aperture. Only applicable if ``function`` is 'Sum'.
    * ``bg_spec_add_results`` (:class:`~jdaviz.core.template_mixin.AddResults`)
    * :meth:`extract_bg_spectrum`
    * ``aperture_method`` (:class:`~jdaviz.core.template_mixin.SelectPluginComponent`):
      Method to use for extracting spectrum (and background, if applicable).
    * ``add_results`` (:class:`~jdaviz.core.template_mixin.AddResults`)
    * :meth:`extract`
    """
    template_file = __file__, "spectral_extraction.vue"
    uses_active_status = Bool(True).tag(sync=True)
    show_live_preview = Bool(True).tag(sync=True)

    active_step = Unicode().tag(sync=True)

    resulting_product_name = Unicode("spectrum").tag(sync=True)
    do_auto_extraction = True
    # whether wavelength dependent options should be exposed to the user (in the UI)
    wavelength_dependent_available = Bool(True).tag(sync=True)
    bg_export_available = Bool(True).tag(sync=True)

    wavelength_dependent = Bool(False).tag(sync=True)
    reference_spectral_value = FloatHandleEmpty().tag(sync=True)
    slice_spectral_value = Float().tag(sync=True)

    bg_items = List([]).tag(sync=True)
    bg_selected = Any('').tag(sync=True)
    bg_selected_validity = Dict().tag(sync=True)
    bg_scale_factor = Float(1).tag(sync=True)
    bg_wavelength_dependent = Bool(False).tag(sync=True)

    bg_spec_per_spaxel = Bool(False).tag(sync=True)
    bg_spec_results_label = Unicode().tag(sync=True)
    bg_spec_results_label_default = Unicode().tag(sync=True)
    bg_spec_results_label_auto = Bool(True).tag(sync=True)
    bg_spec_results_label_invalid_msg = Unicode('').tag(sync=True)
    bg_spec_results_label_overwrite = Bool().tag(sync=True)
    bg_spec_add_to_viewer_items = List().tag(sync=True)
    bg_spec_add_to_viewer_selected = Unicode().tag(sync=True)
    bg_spec_spinner = Bool(False).tag(sync=True)

    function_items = List().tag(sync=True)
    function_selected = Unicode('Sum').tag(sync=True)
    filename = Unicode().tag(sync=True)
    extraction_available = Bool(False).tag(sync=True)

    results_units = Unicode().tag(sync=True)
    spectrum_y_units = Unicode().tag(sync=True)
    flux_units = Unicode().tag(sync=True)
    sb_units = Unicode().tag(sync=True)

    aperture_method_items = List().tag(sync=True)
    aperture_method_selected = Unicode('Center').tag(sync=True)

    conflicting_aperture_and_function = Bool(False).tag(sync=True)
    conflicting_aperture_error_message = Unicode('Aperture method Exact cannot be selected along'
                                                 ' with Min or Max.').tag(sync=True)

    # export_enabled controls whether saving to a file is enabled via the UI.  This
    # is a temporary measure to allow server-installations to disable saving server-side until
    # saving client-side is supported
    export_enabled = Bool(True).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # description displayed under plugin title in tray
        self._plugin_description = 'Extract a spectrum from a spectral cube.'

        self.extracted_spec = None

        self.dataset.filters = ['is_flux_cube']

        # TODO: in the future this could be generalized with support in SelectPluginComponent
        self.aperture._default_text = 'Entire Cube'
        self.aperture._manual_options = ['Entire Cube']
        self.aperture.items = [{"label": "Entire Cube"}]
        self.aperture._subset_selected_changed_callback = self._update_extract
        # need to reinitialize choices since we overwrote items and some subsets may already
        # exist.
        self.aperture._initialize_choices()
        self.aperture.select_default()

        self.background = ApertureSubsetSelect(self,
                                               'bg_items',
                                               'bg_selected',
                                               'bg_selected_validity',
                                               'bg_scale_factor',
                                               dataset='dataset',
                                               multiselect=None,
                                               default_text='None',
                                               subset_selected_changed_callback=self._update_extract)  # noqa

        self.bg_spec_add_results = AddResults(self, 'bg_spec_results_label',
                                              'bg_spec_results_label_default',
                                              'bg_spec_results_label_auto',
                                              'bg_spec_results_label_invalid_msg',
                                              'bg_spec_results_label_overwrite',
                                              'bg_spec_add_to_viewer_items',
                                              'bg_spec_add_to_viewer_selected')
        self.bg_spec_add_results.viewer.filters = ['is_slice_indicator_viewer']
        self.bg_spec_results_label_default = f'background-{self.resulting_product_name}'

        self.function = SelectPluginComponent(
            self,
            items='function_items',
            selected='function_selected',
            manual_options=['Mean', 'Min', 'Max', 'Sum']
        )
        self.aperture_method_manual_options = ['Exact', 'Center']
        self.aperture_method = SelectPluginComponent(
            self,
            items='aperture_method_items',
            selected='aperture_method_selected',
            manual_options=self.aperture_method_manual_options
        )
        self._set_default_results_label()
        self.add_results.viewer.filters = ['is_slice_indicator_viewer']

        self.session.hub.subscribe(self, SliceValueUpdatedMessage,
                                   handler=self._on_slice_changed)
        self.hub.subscribe(self, GlobalDisplayUnitChanged,
                           handler=self._on_global_display_unit_changed)

        self._update_disabled_msg()

        if self.app.state.settings.get('server_is_remote', False):
            # when the server is remote, saving the file in python would save on the server, not
            # on the user's machine, so export support in cubeviz should be disabled
            self.export_enabled = False

    @property
    def user_api(self):
        expose = ['show_live_preview', 'dataset', 'function', 'aperture',
                  'background', 'bg_wavelength_dependent',
                  'bg_spec_per_spaxel', 'bg_spec_add_results', 'extract_bg_spectrum',
                  'add_results', 'extract',
                  'wavelength_dependent', 'reference_spectral_value',
                  'aperture_method']

        return PluginUserApi(self, expose=expose)

    @observe('dataset_items')
    def _update_disabled_msg(self, msg={}):
        for data in self.app.data_collection:
            if data.data.ndim == 3:
                self.disabled_msg = ''
                break
        else:
            # no cube-like data loaded.  Once loaded, the parser will unset this
            self.disabled_msg = (
                f"{self.__class__.__name__} requires a 3d cube dataset to be loaded, "
                "please load data to enable this plugin."
            )

    @property
    def live_update_subscriptions(self):
        return {'data': ('dataset',), 'subset': ('aperture', 'background')}

    def __call__(self, add_data=True):
        return self.extract(add_data=add_data)

    @property
    def slice_display_unit_name(self):
        return 'spectral'

    @property
    def spatial_axes(self):
        # Collapse an e.g. 3D spectral cube to 1D spectrum, assuming that last axis
        # is always wavelength. This may need adjustment after the following
        # specutils PR is merged: https://github.com/astropy/specutils/pull/1033
        return (0, 1)

    @property
    def slice_indicator_viewers(self):
        return [v for v in self.app._viewer_store.values() if isinstance(v, WithSliceIndicator)]

    @observe('active_step', 'is_active')
    def _active_step_changed(self, *args):
        self.aperture._set_mark_visiblities(self.active_step in ('', 'ap', 'extract'))
        self.background._set_mark_visiblities(self.active_step == 'bg')
        self.marks['bg_extract'].visible = self.active_step == 'bg'

    @property
    def slice_plugin(self):
        return self.app._jdaviz_helper.plugins['Slice']

    @observe('aperture_items')
    @skip_if_not_tray_instance()
    def _aperture_items_changed(self, msg):
        if not self.do_auto_extraction:
            return
        if not hasattr(self, 'aperture'):
            return
        orig_labels = [item['label'] for item in msg['old']]
        for item in msg['new']:
            if item['label'] not in orig_labels:
                if item.get('type') != 'spatial':
                    continue
                subset_lbl = item.get('label')
                try:
                    self._extract_in_new_instance(subset_lbl=subset_lbl,
                                                  auto_update=True, add_data=True)
                except Exception:
                    msg = SnackbarMessage(
                        f"Automatic {self.resulting_product_name} extraction for {subset_lbl} failed",  # noqa
                        color='error', sender=self, timeout=10000)
                else:
                    msg = SnackbarMessage(
                        f"Automatic {self.resulting_product_name} extraction for {subset_lbl} successful",  # noqa
                        color='success', sender=self)
                self.app.hub.broadcast(msg)

    def _extract_in_new_instance(self, dataset=None, function='Sum', subset_lbl=None,
                                 auto_update=False, add_data=False):
        # create a new instance of the Spectral Extraction plugin (to not affect the instance in
        # the tray) and extract the entire cube with defaults.
        plg = self.new()
        plg.dataset.selected = self.dataset.selected
        if subset_lbl is not None:
            plg.aperture.selected = subset_lbl
        plg.aperture_method.selected = 'Center'
        plg.function.selected = function
        plg.add_results.auto_update_result = auto_update
        # all other settings remain at their plugin defaults
        return plg(add_data=add_data)

    @observe('wavelength_dependent', 'bg_wavelength_dependent')
    def _wavelength_dependent_changed(self, *args):
        if self.wavelength_dependent:
            self.reference_spectral_value = self.slice_plugin.value
        else:
            self.bg_wavelength_dependent = False
        # NOTE: this can be redundant in the case where reference_spectral_value changed and
        # triggers the observe, but we need to ensure it is updated if reference_spectral_value
        # is unchanged
        self._update_mark_scale()

    def _on_slice_changed(self, msg):
        self.slice_spectral_value = msg.value

    def vue_goto_reference_spectral_value(self, *args):
        self.slice_plugin.value = self.reference_spectral_value

    def vue_adopt_slice_as_reference(self, *args):
        self.reference_spectral_value = self.slice_plugin.value

    @observe('reference_spectral_value', 'slice_spectral_value')
    def _update_mark_scale(self, *args):
        if not self.wavelength_dependent:
            self.aperture.scale_factor = 1.0
        else:
            self.aperture.scale_factor = self.slice_spectral_value/self.reference_spectral_value
        if not self.bg_wavelength_dependent:
            self.background.scale_factor = 1.0
        else:
            self.background.scale_factor = self.slice_spectral_value/self.reference_spectral_value

    def _on_global_display_unit_changed(self, msg=None):
        if msg is None:
            self.flux_units = str(self.app._get_display_unit('flux'))
            self.sb_units = str(self.app._get_display_unit('sb'))
            self.spectrum_y_units = str(self.app._get_display_unit('spectral_y'))
        elif msg.axis == 'flux':
            self.flux_units = str(msg.unit)
        elif msg.axis == 'sb':
            self.sb_units = str(msg.unit)
        elif msg.axis == 'spectral_y':
            self.spectrum_y_units = str(msg.unit)
            # no need to update results_units as separate messages will have been
            # sent by unit conversion for flux and/or sb.
            # updates to spectrum_y_units will trigger updating the extraction preview
            return
        else:
            # ignore
            return
        # update results_units based on flux_units, sb_units, and currently selected function
        self._update_results_units()

    @observe('function_selected')
    def _update_results_units(self, *args):
        # NOTE this is also called by _on_global_display_unit_changed
        # after flux_units and/or sb_units is set.
        # results_units is ONLY used for the warning in the UI, so does not
        # need to trigger an update to the preview
        if self.function_selected.lower() == 'sum':
            self.results_units = self.flux_units
        else:
            self.results_units = self.sb_units

    @observe('function_selected', 'aperture_method_selected')
    def _update_aperture_method_on_function_change(self, *args):
        if (self.function_selected.lower() in ('min', 'max') and
                self.aperture_method_selected.lower() != 'center'):
            self.conflicting_aperture_and_function = True
        else:
            self.conflicting_aperture_and_function = False

    @property
    def cube(self):
        return self.dataset.selected_dc_item

    @property
    def uncert_cube(self):
        if (hasattr(self._app._jdaviz_helper, '_loaded_flux_cube') and
                hasattr(self.app._jdaviz_helper, '_loaded_uncert_cube') and
                self.dataset.selected == self._app._jdaviz_helper._loaded_flux_cube.label):
            return self._app._jdaviz_helper._loaded_uncert_cube
        else:
            # TODO: allow selecting or associating an uncertainty cube?
            return None

    @property
    def mask_cube(self):
        if (hasattr(self._app._jdaviz_helper, '_loaded_flux_cube') and
                hasattr(self.app._jdaviz_helper, '_loaded_mask_cube') and
                self.dataset.selected == self._app._jdaviz_helper._loaded_flux_cube.label):
            return self._app._jdaviz_helper._loaded_mask_cube
        else:
            # TODO: allow selecting or associating a mask/DQ cube?
            return None

    @property
    def slice_display_unit(self):
        return astropy.units.Unit(self.app._get_display_unit(self.slice_display_unit_name))

    @property
    def inverted_mask_non_science(self):
        # Aperture masks begin by removing from consideration any pixel
        # set to NaN, which corresponds to a pixel on the "non-science" portions
        # of the detector. For JWST spectral cubes, these pixels are also marked in
        # the DQ array with flag `513`. Also respect the loaded mask, if it exists.
        # This "inverted mask" is `True` where the data are included, `False` where excluded.
        mask_non_science = np.isnan(self.dataset.selected_obj.flux.value)
        if self.mask_cube is not None:
            mask_non_science = np.logical_or(self.mask_cube.get_component('flux').data,
                                             mask_non_science)
        return np.logical_not(mask_non_science).astype(float)

    @property
    def aperture_weight_mask(self):
        # Exact slice mask of cone or cylindrical aperture through the cube. `weight_mask` is
        # a 3D array with fractions of each pixel within an aperture at each
        # wavelength, on the range [0, 1].
        if self.aperture.selected == self.aperture.default_text:
            # Entire Cube
            return self.inverted_mask_non_science

        return (
            self.inverted_mask_non_science *
            self.aperture.get_mask(
                self.dataset.selected_obj,
                self.aperture_method_selected,
                self.slice_display_unit,
                self.spatial_axes,
                self.reference_spectral_value if self.wavelength_dependent else None)
        )

    @property
    def bg_weight_mask(self):
        if self.background.selected == self.background.default_text:
            # NO background
            return np.zeros_like(self.dataset.selected_obj.flux.value)

        return (
            self.inverted_mask_non_science *
            self.background.get_mask(
                self.dataset.selected_obj,
                self.aperture_method_selected,
                self.slice_display_unit,
                self.spatial_axes,
                self.reference_spectral_value if self.bg_wavelength_dependent else None)
        )

    @property
    def aperture_area_along_spectral(self):
        # Weight mask summed along the spatial axes so that we get area of the aperture, in pixels,
        # as a function of wavelength.
        # To convert to steradians, multiply by self.cube.meta.get('PIXAR_SR', 1.0)
        return np.sum(self.aperture_weight_mask, axis=self.spatial_axes)

    @property
    def bg_area_along_spectral(self):
        return np.sum(self.bg_weight_mask, axis=self.spatial_axes)

    def _extract_from_aperture(self, cube, uncert_cube, mask_cube, aperture,
                               weight_mask, wavelength_dependent,
                               selected_func, **kwargs):
        # This plugin collapses over the *spatial axes* (optionally over a spatial subset,
        # defaults to ``No Subset``). Since the Cubeviz parser puts the fluxes
        # and uncertainties in different glue Data objects, we translate the spectral
        # cube and its uncertainties into separate NDDataArrays, then combine them:
        if not isinstance(aperture, ApertureSubsetSelect):
            raise ValueError("aperture must be an ApertureSubsetSelect object")
        if aperture.selected != aperture.default_text:
            nddata = cube.get_subset_object(
                subset_id=aperture.selected, cls=NDDataArray
            )
            if uncert_cube:
                uncertainties = uncert_cube.get_subset_object(
                    subset_id=aperture.selected, cls=StdDevUncertainty
                )
            else:
                uncertainties = None

            if self.aperture_method_selected.lower() == 'center':
                flux = nddata.data << nddata.unit
            else:  # exact (min/max not allowed here)
                # Apply the fractional pixel array to the flux cube
                flux = (weight_mask * nddata.data) << nddata.unit
            # Boolean cube which is True outside of the aperture
            # (i.e., the numpy boolean mask convention)
            mask = np.isclose(weight_mask, 0)

            # composite subset masks are in `nddata.mask`:
            if nddata.mask is not None and np.all(weight_mask == 0):
                mask &= nddata.mask

        else:
            nddata = cube.get_object(cls=NDDataArray)
            if uncert_cube:
                uncertainties = uncert_cube.get_object(cls=StdDevUncertainty)
            else:
                uncertainties = None
            flux = nddata.data << nddata.unit
            mask = nddata.mask

        # Use the spectral coordinate from the WCS:
        if '_orig_spec' in cube.meta:
            wcs = cube.meta['_orig_spec'].wcs.spectral
        elif hasattr(cube.coords, 'spectral'):
            wcs = cube.coords.spectral
        elif hasattr(cube.coords, 'spectral_wcs'):
            # This is the attribute for a PaddedSpectrumWCS in the 3D case
            wcs = cube.coords.spectral_wcs
        else:
            wcs = None

        # Filter out NaNs (False = good)
        mask = np.logical_or(mask, np.isnan(flux))

        # Also apply the cube's original mask array
        if mask_cube:
            snackbar_message = SnackbarMessage(
                "Note: Applied loaded mask cube during extraction",
                color="warning",
                sender=self)
            self.hub.broadcast(snackbar_message)
            mask_from_cube = mask_cube.get_component('flux').data.copy()
            # Some mask cubes have NaNs where they are not masked instead of 0
            mask_from_cube[np.where(np.isnan(mask_from_cube))] = 0
            mask = np.logical_or(mask, mask_from_cube.astype('bool'))

        nddata_reshaped = NDDataArray(
            flux, mask=mask, uncertainty=uncertainties, wcs=wcs, meta=nddata.meta
        )
        # by default we want to use operation_ignores_mask=True in nddata:
        kwargs.setdefault("operation_ignores_mask", True)
        # by default we want to propagate uncertainties:
        kwargs.setdefault("propagate_uncertainties", True)

        if selected_func == 'mean':
            # Use built-in sum function to collapse NDDataArray
            collapsed_sum_for_mean = nddata_reshaped.sum(axis=self.spatial_axes, **kwargs)
            # But we still need the mean function for everything except flux
            collapsed_as_mean = nddata_reshaped.mean(axis=self.spatial_axes, **kwargs)

            # Then normalize the flux based on the fractional pixel array
            flux_for_mean = (collapsed_sum_for_mean.data /
                             np.sum(weight_mask, axis=self.spatial_axes)) << nddata_reshaped.unit
            # Combine that information into a new NDDataArray
            collapsed_nddata = NDDataArray(flux_for_mean, mask=collapsed_as_mean.mask,
                                           uncertainty=collapsed_as_mean.uncertainty,
                                           wcs=collapsed_as_mean.wcs,
                                           meta=collapsed_as_mean.meta)
        elif selected_func == 'sum':
            collapsed_nddata = getattr(nddata_reshaped, selected_func)(
                axis=self.spatial_axes, **kwargs
            )  # returns an NDDataArray

            # Remove per solid angle denominator to turn sb into flux
            sq_angle_unit = check_if_unit_is_per_solid_angle(collapsed_nddata.unit,
                                                             return_unit=True)
            if sq_angle_unit is not None:
                # convert aperture area in steradians to the selected square angle unit
                # NOTE: just forcing these units for now!! this is in steradians and
                # needs to be converted to the selected square angle unit but for now just
                # force to correct units
                if sq_angle_unit == u.sr:
                    aperture_area = self.cube.meta.get('PIXAR_SR', 1.0) * sq_angle_unit
                else:
                    aperture_area = 1 * sq_angle_unit
                collapsed_nddata = collapsed_nddata.multiply(aperture_area,
                                                             propagate_uncertainties=True)
        else:
            collapsed_nddata = getattr(nddata_reshaped, selected_func)(
                axis=self.spatial_axes, **kwargs
            )  # returns an NDDataArray

        return self._return_extracted(cube, wcs, collapsed_nddata)

    def _return_extracted(self, cube, wcs, collapsed_nddata):
        # Convert to Spectrum1D, with the spectral axis in correct units:
        if hasattr(cube.coords, 'spectral_wcs'):
            target_wave_unit = cube.coords.spectral_wcs.world_axis_units[0]
        elif hasattr(cube.coords, 'spectral'):
            target_wave_unit = cube.coords.spectral.world_axis_units[0]
        else:
            target_wave_unit = None

        if target_wave_unit == '':
            target_wave_unit = 'pix'

        flux = collapsed_nddata.data << collapsed_nddata.unit
        mask = collapsed_nddata.mask
        uncertainty = collapsed_nddata.uncertainty

        collapsed_spec = _return_spectrum_with_correct_units(
            flux, wcs, collapsed_nddata.meta, data_type='flux',
            target_wave_unit=target_wave_unit,
            uncertainty=uncertainty,
            mask=mask
        )
        return collapsed_spec

    def _preview_x_from_extracted(self, extracted):
        return extracted.spectral_axis

    def _preview_y_from_extracted(self, extracted):
        """
        Convert y-axis units of extraction preview to display units,
        if necessary.
        """

        if extracted.flux.unit != self.spectrum_y_units:

            eqv = all_flux_unit_conversion_equivs(self.dataset.selected_obj.meta.get('PIXAR_SR', 1.0),  # noqa
                                                  self.dataset.selected_obj.spectral_axis)

            return flux_conversion_general(extracted.flux.value, extracted.flux.unit,
                                           self.spectrum_y_units, eqv)

        return extracted.flux

    @with_spinner()
    def extract(self, return_bg=False, add_data=True, **kwargs):
        """
        Extract the spectrum from the data cube according to the plugin inputs.

        Parameters
        ----------
        return_bg : bool, optional
            Whether to also return the spectrum of the background, if applicable.
        add_data : bool, optional
            Whether to load the resulting data back into the application according to
            ``add_results``.
        kwargs : dict
            Additional keyword arguments passed to the NDDataArray collapse operation.
            Examples include ``propagate_uncertainties`` and ``operation_ignores_mask``.
        """
        if self.conflicting_aperture_and_function:
            raise ValueError(self.conflicting_aperture_error_message)
        if self.aperture.selected == self.background.selected:
            raise ValueError("aperture and background cannot be set to the same subset")

        selected_func = self.function_selected.lower()
        spec = self._extract_from_aperture(self.cube, self.uncert_cube, self.mask_cube,
                                           self.aperture, self.aperture_weight_mask,
                                           self.wavelength_dependent,
                                           selected_func, **kwargs)

        bg_spec = self.extract_bg_spectrum(add_data=False, bg_spec_per_spaxel=False)
        if bg_spec is not None:
            spec = spec - bg_spec

        # per https://jwst-docs.stsci.edu/jwst-near-infrared-camera/nircam-performance/nircam-absolute-flux-calibration-and-zeropoints # noqa
        pix_scale_factor = self.cube.meta.get('PIXAR_SR', 1.0)
        spec.meta['_pixel_scale_factor'] = pix_scale_factor

        # stuff for exporting to file
        self.extracted_spec = spec
        self.extraction_available = True
        fname_label = self.dataset_selected.replace("[", "_").replace("]", "")
        self.filename = f"extracted_{selected_func}_{fname_label}.fits"

        if add_data:
            if default_color := self.aperture.selected_item.get('color', None):
                spec.meta['_default_color'] = default_color
            self.add_results.add_results_from_plugin(spec)

            snackbar_message = SnackbarMessage(
                f"{self.resulting_product_name.title()} extracted successfully.",
                color="success",
                sender=self)
            self.hub.broadcast(snackbar_message)

        if return_bg:
            return spec, bg_spec
        return spec

    @with_spinner('bg_spec_spinner')
    def extract_bg_spectrum(self, add_data=False, **kwargs):
        """
        Create a background 1D spectrum from the input parameters defined in the plugin.

        If ``function`` is 'sum', then the value is scaled by the relative ratios of the area
        (along the spectral axis) of ``aperture`` to ``background``.

        Parameters
        ----------
        add_data : bool
            Whether to add the resulting spectrum to the application, according to the options
            defined in the plugin.
        kwargs : dict
            Additional keyword arguments passed to the NDDataArray collapse operation.
            Examples include ``propagate_uncertainties`` and ``operation_ignores_mask``.
        """
        # allow internal calls to override the behavior of the bg_spec_per_spaxel traitlet
        bg_spec_per_spaxel = kwargs.pop('bg_spec_per_spaxel', self.bg_spec_per_spaxel)
        if self.background.selected != self.background.default_text:
            bg_spec = self._extract_from_aperture(self.cube, self.uncert_cube, self.mask_cube,
                                                  self.background, self.bg_weight_mask,
                                                  self.bg_wavelength_dependent,
                                                  self.function_selected.lower(), **kwargs)
            if self.function_selected.lower() == 'sum':
                if not bg_spec_per_spaxel:
                    # then scale according to aperture areas across the spectral axis (allowing for
                    # independent wavelength-dependence btwn the aperture and background)
                    bg_spec *= self.aperture_area_along_spectral / self.bg_area_along_spectral
        else:
            bg_spec = None

        if add_data:
            if bg_spec is None:
                raise ValueError(f"Background is set to {self.background.selected}")
            self.bg_spec_add_results.add_results_from_plugin(bg_spec, replace=False)

        return bg_spec

    def vue_spectral_extraction(self, *args, **kwargs):
        try:
            self.extract(add_data=True)
        except Exception as e:
            self.hub.broadcast(SnackbarMessage(
                f"Extraction failed: {repr(e)}",
                sender=self, color="error"))

    def vue_create_bg_spec(self, *args, **kwargs):
        self.extract_bg_spectrum(add_data=True)

    @observe('aperture_selected', 'function_selected')
    def _set_default_results_label(self, event={}):
        if not hasattr(self, 'aperture'):
            return
        if self.aperture.selected == self.aperture.default_text:
            self.results_label_default = f"{self.resulting_product_name.title()} ({self.function_selected.lower()})"  # noqa
        else:
            self.results_label_default = f"{self.resulting_product_name.title()} ({self.aperture_selected}, {self.function_selected.lower()})"  # noqa

    @cached_property
    def marks(self):
        if not self._tray_instance:
            return {}
        # TODO: iterate over self.slice_indicator_viewers and handle adding/removing viewers
        sv = self.slice_indicator_viewers[0]
        marks = {'extract': PluginLine(sv, visible=self.is_active),
                 'bg_extract': PluginLine(sv,
                                          line_style='dotted',
                                          visible=self.is_active and self.active_step == 'bg')}
        sv.figure.marks = sv.figure.marks + [marks['extract'], marks['bg_extract']]
        return marks

    def _clear_marks(self):
        for mark in self.marks.values():
            if mark.visible:
                mark.visible = False

    @observe('is_active', 'show_live_preview',
             'dataset_selected', 'aperture_selected', 'bg_selected',
             'wavelength_dependent', 'bg_wavelength_dependent', 'reference_spectral_value',
             'function_selected',
             'aperture_method_selected',
             'spectrum_y_units',
             'previews_temp_disabled')
    def _live_update_marks(self, event={}):
        if self.spectrum_y_units == '':
            # ensure that units are populated
            # which in turn will make a call back here
            # from the observe on spectrum_y_units
            self._on_global_display_unit_changed(None)
            return
        self._update_marks(event)

    @skip_if_not_tray_instance()
    def _update_marks(self, event={}):
        visible = self.show_live_preview and self.is_active

        if not visible:
            self._clear_marks()
            return

        # ensure the correct visibility, always (whether or not there have been updates)
        self.marks['bg_extract'].visible = self.active_step == 'bg' and self.bg_selected != self.background.default_text  # noqa
        self.marks['extract'].visible = True

        # _live_update_extract will skip if no updates since last active
        self._live_update_extract(event)

    @skip_if_no_updates_since_last_active()
    @with_temp_disable(timeout=0.4)
    def _live_update_extract(self, event={}):
        self._update_extract()

    @skip_if_not_tray_instance()
    def _update_extract(self):
        try:
            ext, bg_extract = self.extract(return_bg=True, add_data=False)
        except (ValueError, Exception):
            self._clear_marks()
            return False

        self.marks['extract'].update_xy(self._preview_x_from_extracted(ext),
                                        self._preview_y_from_extracted(ext))

        if bg_extract is None:
            self.marks['bg_extract'].clear()
            self.marks['bg_extract'].visible = False
        else:
            self.marks['bg_extract'].update_xy(self._preview_x_from_extracted(bg_extract),
                                               self._preview_y_from_extracted(bg_extract))
