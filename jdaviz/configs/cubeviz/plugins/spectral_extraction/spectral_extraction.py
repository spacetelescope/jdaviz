import os
from pathlib import Path

import numpy as np
import astropy
import astropy.units as u
from astropy.nddata import (
    NDDataArray, StdDevUncertainty
)
from functools import cached_property
from traitlets import Any, Bool, Dict, Float, List, Unicode, observe

from jdaviz.core.custom_traitlets import FloatHandleEmpty
from jdaviz.core.events import SnackbarMessage, SliceValueUpdatedMessage
from jdaviz.core.marks import PluginLine
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin,
                                        DatasetSelectMixin,
                                        SelectPluginComponent,
                                        ApertureSubsetSelectMixin,
                                        ApertureSubsetSelect,
                                        AddResults, AddResultsMixin,
                                        skip_if_no_updates_since_last_active,
                                        skip_if_not_tray_instance,
                                        with_spinner, with_temp_disable)
from jdaviz.core.user_api import PluginUserApi
from jdaviz.configs.cubeviz.plugins.parsers import _return_spectrum_with_correct_units


__all__ = ['SpectralExtraction']


@tray_registry(
    'cubeviz-spectral-extraction', label="Spectral Extraction", viewer_requirements='spectrum'
)
class SpectralExtraction(PluginTemplateMixin, ApertureSubsetSelectMixin,
                         DatasetSelectMixin, AddResultsMixin):
    """
    See the :ref:`Spectral Extraction Plugin Documentation <spex>` for more details.

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
    * ``background`` (:class:`~jdaviz.comre.template_mixin.ApertureSubsetSelect`):
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
    * :meth:`collapse`
    """
    template_file = __file__, "spectral_extraction.vue"
    uses_active_status = Bool(True).tag(sync=True)
    show_live_preview = Bool(True).tag(sync=True)

    active_step = Unicode().tag(sync=True)

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
    extracted_spec_available = Bool(False).tag(sync=True)
    overwrite_warn = Bool(False).tag(sync=True)

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

        self._default_spectrum_viewer_reference_name = kwargs.get(
            "spectrum_viewer_reference_name", "spectrum-viewer"
        )

        super().__init__(*args, **kwargs)

        self.extracted_spec = None

        self.dataset.filters = ['is_flux_cube']

        # TODO: in the future this could be generalized with support in SelectPluginComponent
        self.aperture._default_text = 'Entire Cube'
        self.aperture._manual_options = ['Entire Cube']
        self.aperture.items = [{"label": "Entire Cube"}]
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
                                               default_text='None')

        self.bg_spec_add_results = AddResults(self, 'bg_spec_results_label',
                                              'bg_spec_results_label_default',
                                              'bg_spec_results_label_auto',
                                              'bg_spec_results_label_invalid_msg',
                                              'bg_spec_results_label_overwrite',
                                              'bg_spec_add_to_viewer_items',
                                              'bg_spec_add_to_viewer_selected')
        self.bg_spec_add_results.viewer.filters = ['is_spectrum_viewer']
        self.bg_spec_results_label_default = 'background-spectrum'

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
        self.add_results.viewer.filters = ['is_spectrum_viewer']

        self.session.hub.subscribe(self, SliceValueUpdatedMessage,
                                   handler=self._on_slice_changed)

        if self.app.state.settings.get('server_is_remote', False):
            # when the server is remote, saving the file in python would save on the server, not
            # on the user's machine, so export support in cubeviz should be disabled
            self.export_enabled = False

        for data in self.app.data_collection:
            if len(data.data.shape) == 3:
                break
        else:
            # no cube-like data loaded.  Once loaded, the parser will unset this
            # TODO: change to an event listener on AddDataMessage
            self.disabled_msg = (
                "Spectral Extraction requires a single dataset to be loaded into Cubeviz, "
                "please load data to enable this plugin."
            )

    @property
    def user_api(self):
        expose = ['dataset', 'function', 'aperture',
                  'background', 'bg_wavelength_dependent',
                  'bg_spec_per_spaxel', 'bg_spec_add_results', 'extract_bg_spectrum',
                  'add_results', 'extract',
                  'wavelength_dependent', 'reference_spectral_value',
                  'aperture_method']

        return PluginUserApi(self, expose=expose)

    @property
    def live_update_subscriptions(self):
        return {'data': ('dataset',), 'subset': ('aperture', 'background')}

    def __call__(self, add_data=True):
        return self.extract(add_data=add_data)

    @property
    def slice_display_unit_name(self):
        return 'spectral'

    @observe('active_step', 'is_active')
    def _active_step_changed(self, *args):
        self.aperture._set_mark_visiblities(self.active_step in ('', 'ap', 'ext'))
        self.background._set_mark_visiblities(self.active_step == 'bg')
        self.marks['bg_spec'].visible = self.active_step == 'bg'

    @property
    def slice_plugin(self):
        return self.app._jdaviz_helper.plugins['Slice']

    @observe('aperture_items')
    @skip_if_not_tray_instance()
    def _aperture_items_changed(self, msg):
        if not hasattr(self, 'aperture'):
            return
        for item in msg['new']:
            if item not in msg['old']:
                if item.get('type') != 'spatial':
                    continue
                subset_lbl = item.get('label')
                try:
                    self._extract_in_new_instance(subset_lbl=subset_lbl,
                                                  auto_update=True, add_data=True)
                except Exception:
                    msg = SnackbarMessage(
                        f"Automatic spectrum extraction for {subset_lbl} failed",
                        color='error', sender=self, timeout=10000)
                else:
                    msg = SnackbarMessage(
                        f"Automatic spectrum extraction for {subset_lbl} successful",
                        color='success', sender=self)
                self.app.hub.broadcast(msg)

    def _extract_in_new_instance(self, dataset=None, function='Sum', subset_lbl=None,
                                 auto_update=False, add_data=False):
        # create a new instance of the Spectral Extraction plugin (to not affect the instance in
        # the tray) and extract the entire cube with defaults.
        if dataset is None:
            if self._app._jdaviz_helper._loaded_flux_cube is None:
                return
            dataset = self._app._jdaviz_helper._loaded_flux_cube.label
        plg = self.new()
        plg.dataset.selected = dataset
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

    @observe('function_selected', 'aperture_method_selected')
    def _update_aperture_method_on_function_change(self, *args):
        if (self.function_selected.lower() in ('min', 'max') and
                self.aperture_method_selected.lower() != 'center'):
            self.conflicting_aperture_and_function = True
        else:
            self.conflicting_aperture_and_function = False

    @property
    def spectral_cube(self):
        return self.dataset.selected_dc_item

    @property
    def uncert_cube(self):
        if self.dataset.selected == self._app._jdaviz_helper._loaded_flux_cube.label:
            return self._app._jdaviz_helper._loaded_uncert_cube
        else:
            # TODO: allow selecting or associating an uncertainty cube?
            return None

    @property
    def spectral_display_unit(self):
        return astropy.units.Unit(self.app._get_display_unit(self.slice_display_unit_name))

    @property
    def aperture_weight_mask(self):
        # Exact slice mask of cone or cylindrical aperture through the cube. `weight_mask` is
        # a 3D array with fractions of each pixel within an aperture at each
        # wavelength, on the range [0, 1].
        if self.aperture.selected == self.aperture.default_text:
            # Entire Cube
            return np.ones_like(self.dataset.selected_obj.flux.value)
        return self.aperture.get_mask(self.dataset.selected_obj,
                                      self.aperture_method_selected,
                                      self.spectral_display_unit,
                                      self.reference_spectral_value if self.wavelength_dependent else None)  # noqa

    @property
    def bg_weight_mask(self):
        if self.background.selected == self.background.default_text:
            # NO background
            return np.zeros_like(self.dataset.selected_obj.flux.value)
        return self.background.get_mask(self.dataset.selected_obj,
                                        self.aperture_method_selected,
                                        self.spectral_display_unit,
                                        self.reference_spectral_value if self.bg_wavelength_dependent else None)  # noqa

    @property
    def aperture_area_along_spectral(self):
        # Weight mask summed along the spatial axes so that we get area of the aperture, in pixels,
        # as a function of wavelength.
        # To convert to steradians, multiply by self.spectral_cube.meta.get('PIXAR_SR', 1.0)
        return np.sum(self.aperture_weight_mask, axis=(0, 1))

    @property
    def bg_area_along_spectral(self):
        return np.sum(self.bg_weight_mask, axis=(0, 1))

    def _extract_from_aperture(self, spectral_cube, uncert_cube, aperture,
                               weight_mask, wavelength_dependent,
                               selected_func, **kwargs):
        # This plugin collapses over the *spatial axes* (optionally over a spatial subset,
        # defaults to ``No Subset``). Since the Cubeviz parser puts the fluxes
        # and uncertainties in different glue Data objects, we translate the spectral
        # cube and its uncertainties into separate NDDataArrays, then combine them:
        if not isinstance(aperture, ApertureSubsetSelect):
            raise ValueError("aperture must be an ApertureSubsetSelect object")
        if aperture.selected != aperture.default_text:
            nddata = spectral_cube.get_subset_object(
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
            nddata = spectral_cube.get_object(cls=NDDataArray)
            if uncert_cube:
                uncertainties = uncert_cube.get_object(cls=StdDevUncertainty)
            else:
                uncertainties = None
            flux = nddata.data << nddata.unit
            mask = nddata.mask
        # Use the spectral coordinate from the WCS:
        if '_orig_spec' in spectral_cube.meta:
            wcs = spectral_cube.meta['_orig_spec'].wcs.spectral
        elif hasattr(spectral_cube.coords, 'spectral'):
            wcs = spectral_cube.coords.spectral
        else:
            wcs = None

        # Filter out NaNs (False = good)
        mask = np.logical_or(mask, np.isnan(flux))

        nddata_reshaped = NDDataArray(
            flux, mask=mask, uncertainty=uncertainties, wcs=wcs, meta=nddata.meta
        )
        # by default we want to use operation_ignores_mask=True in nddata:
        kwargs.setdefault("operation_ignores_mask", True)
        # by default we want to propagate uncertainties:
        kwargs.setdefault("propagate_uncertainties", True)

        # Collapse an e.g. 3D spectral cube to 1D spectrum, assuming that last axis
        # is always wavelength. This may need adjustment after the following
        # specutils PR is merged: https://github.com/astropy/specutils/pull/1033
        spatial_axes = (0, 1)
        if selected_func == 'mean':
            # Use built-in sum function to collapse NDDataArray
            collapsed_sum_for_mean = nddata_reshaped.sum(axis=spatial_axes, **kwargs)
            # But we still need the mean function for everything except flux
            collapsed_as_mean = nddata_reshaped.mean(axis=spatial_axes, **kwargs)

            # Then normalize the flux based on the fractional pixel array
            flux_for_mean = (collapsed_sum_for_mean.data /
                             np.sum(weight_mask, axis=spatial_axes)) << nddata_reshaped.unit
            # Combine that information into a new NDDataArray
            collapsed_nddata = NDDataArray(flux_for_mean, mask=collapsed_as_mean.mask,
                                           uncertainty=collapsed_as_mean.uncertainty,
                                           wcs=collapsed_as_mean.wcs,
                                           meta=collapsed_as_mean.meta)
        elif selected_func == 'sum':
            collapsed_nddata = getattr(nddata_reshaped, selected_func)(
                axis=spatial_axes, **kwargs
            )  # returns an NDDataArray
            # Remove per steradian denominator
            if astropy.units.sr in collapsed_nddata.unit.bases:
                aperture_area = (self.aperture_area_along_spectral
                                 * self.spectral_cube.meta.get('PIXAR_SR', 1.0) * u.sr)
                collapsed_nddata = collapsed_nddata.multiply(aperture_area,
                                                             propagate_uncertainties=True)
        else:
            collapsed_nddata = getattr(nddata_reshaped, selected_func)(
                axis=spatial_axes, **kwargs
            )  # returns an NDDataArray
        # Convert to Spectrum1D, with the spectral axis in correct units:
        if hasattr(spectral_cube.coords, 'spectral_wcs'):
            target_wave_unit = spectral_cube.coords.spectral_wcs.world_axis_units[0]
        else:
            target_wave_unit = spectral_cube.coords.spectral.world_axis_units[0]

        if target_wave_unit == '':
            target_wave_unit = 'pix'

        flux = collapsed_nddata.data << collapsed_nddata.unit
        mask = collapsed_nddata.mask
        uncertainty = collapsed_nddata.uncertainty

        collapsed_spec = _return_spectrum_with_correct_units(
            flux, wcs, collapsed_nddata.meta, 'flux',
            target_wave_unit=target_wave_unit,
            uncertainty=uncertainty,
            mask=mask
        )
        return collapsed_spec

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
        spec = self._extract_from_aperture(self.spectral_cube, self.uncert_cube,
                                           self.aperture, self.aperture_weight_mask,
                                           self.wavelength_dependent,
                                           selected_func, **kwargs)

        bg_spec = self.extract_bg_spectrum(add_data=False, bg_spec_per_spaxel=False)
        if bg_spec is not None:
            spec = spec - bg_spec

        # per https://jwst-docs.stsci.edu/jwst-near-infrared-camera/nircam-performance/nircam-absolute-flux-calibration-and-zeropoints # noqa
        pix_scale_factor = self.aperture_area_along_spectral * self.spectral_cube.meta.get('PIXAR_SR', 1.0)  # noqa
        spec.meta['_pixel_scale_factor'] = pix_scale_factor

        # inform the user if scale factor keyword not in metadata
        if 'PIXAR_SR' not in self.spectral_cube.meta:
            snackbar_message = SnackbarMessage(
                ("PIXAR_SR FITS header keyword not found when parsing spectral cube. "
                 "Flux/Surface Brightness will use default scale factor of 1."),
                color="error",
                sender=self)
            self.hub.broadcast(snackbar_message)

        # stuff for exporting to file
        self.extracted_spec = spec
        self.extracted_spec_available = True
        fname_label = self.dataset_selected.replace("[", "_").replace("]", "")
        self.filename = f"extracted_{selected_func}_{fname_label}.fits"

        if add_data:
            if default_color := self.aperture.selected_item.get('color', None):
                spec.meta['_default_color'] = default_color
            self.add_results.add_results_from_plugin(spec)

            snackbar_message = SnackbarMessage(
                "Spectrum extracted successfully.",
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
            bg_spec = self._extract_from_aperture(self.spectral_cube, self.uncert_cube,
                                                  self.background, self.bg_weight_mask,
                                                  self.bg_wavelength_dependent,
                                                  self.function_selected.lower(), **kwargs)
            if self.function_selected.lower() == 'sum':
                if bg_spec_per_spaxel:
                    bg_spec *= 1 / self.bg_area_along_spectral
                else:
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

    def vue_save_as_fits(self, *args):
        self._save_extracted_spec_to_fits()

    def vue_overwrite_fits(self, *args):
        """Attempt to force writing the spectral extraction if the user
        confirms the desire to overwrite."""
        self.overwrite_warn = False
        self._save_extracted_spec_to_fits(overwrite=True)

    def _save_extracted_spec_to_fits(self, overwrite=False, *args):

        if not self.export_enabled:
            # this should never be triggered since this is intended for UI-disabling and the
            # UI section is hidden, but would prevent any JS-hacking
            raise ValueError("Writing out extracted spectrum to file is currently disabled")

        # Make sure file does not end up in weird places in standalone mode.
        path = os.path.dirname(self.filename)
        if path and not os.path.exists(path):
            raise ValueError(f"Invalid path={path}")
        elif (not path or path.startswith("..")) and os.environ.get("JDAVIZ_START_DIR", ""):  # noqa: E501 # pragma: no cover
            filename = Path(os.environ["JDAVIZ_START_DIR"]) / self.filename
        else:
            filename = Path(self.filename).resolve()

        if filename.exists():
            if overwrite:
                # Try to delete the file
                filename.unlink()
                if filename.exists():
                    # Warn the user if the file still exists
                    raise FileExistsError(f"Unable to delete {filename}. Check user permissions.")
            else:
                self.overwrite_warn = True
                return

        filename = str(filename)
        self.extracted_spec.write(filename)

        # Let the user know where we saved the file.
        self.hub.broadcast(SnackbarMessage(
            f"Extracted spectrum saved to {os.path.abspath(filename)}",
                           sender=self, color="success"))

    @observe('aperture_selected', 'function_selected')
    def _set_default_results_label(self, event={}):
        if not hasattr(self, 'aperture'):
            return
        if self.aperture.selected == self.aperture.default_text:
            self.results_label_default = f"Spectrum ({self.function_selected.lower()})"
        else:
            self.results_label_default = f"Spectrum ({self.aperture_selected}, {self.function_selected.lower()})"  # noqa

    @cached_property
    def marks(self):
        if not self._tray_instance:
            return {}
        sv = self.spectrum_viewer
        marks = {'spec': PluginLine(sv, visible=self.is_active),
                 'bg_spec': PluginLine(sv,
                                       line_style='dotted',
                                       visible=self.is_active and self.active_step == 'bg')}
        sv.figure.marks = sv.figure.marks + [marks['spec'], marks['bg_spec']]
        return marks

    def _clear_marks(self):
        for mark in self.marks.values():
            if mark.visible:
                mark.visible = False

    @observe('is_active', 'show_live_preview')
    def _toggle_marks(self, event={}):
        visible = self.show_live_preview and self.is_active

        if not visible:
            self._clear_marks()
        elif event.get('name', '') in ('is_active', 'show_live_preview'):
            # then the marks themselves need to be updated
            self._live_update(event)

    @observe('dataset_selected', 'aperture_selected', 'bg_selected',
             'wavelength_dependent', 'bg_wavelength_dependent', 'reference_spectral_value',
             'function_selected',
             'aperture_method_selected',
             'previews_temp_disabled')
    @skip_if_no_updates_since_last_active()
    @with_temp_disable(timeout=0.4)
    def _live_update(self, event={}):
        if not self._tray_instance:
            return
        if not self.show_live_preview or not self.is_active:
            self._clear_marks()
            return

        try:
            sp, bg_spec = self.extract(return_bg=True, add_data=False)
        except (ValueError, Exception):
            self._clear_marks()
            return

        self.marks['spec'].update_xy(sp.spectral_axis.value, sp.flux.value)
        self.marks['spec'].visible = True

        if bg_spec is None:
            self.marks['bg_spec'].clear()
            self.marks['bg_spec'].visible = False
        else:
            self.marks['bg_spec'].update_xy(bg_spec.spectral_axis.value, bg_spec.flux.value)
            self.marks['bg_spec'].visible = self.active_step == 'bg'
