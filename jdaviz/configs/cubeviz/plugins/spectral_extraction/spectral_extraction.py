import os
from pathlib import Path

import numpy as np
import astropy
from astropy import units as u
from astropy.utils.decorators import deprecated
from astropy.nddata import (
    NDDataArray, StdDevUncertainty
)
from traitlets import Any, Bool, Dict, Float, List, Unicode, observe
from packaging.version import Version
from photutils.aperture import CircularAperture, EllipticalAperture, RectangularAperture
from specutils import Spectrum1D

from jdaviz.core.custom_traitlets import FloatHandleEmpty
from jdaviz.core.events import SnackbarMessage, SliceValueUpdatedMessage
from jdaviz.core.marks import SpectralExtractionPreview
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin,
                                        DatasetSelectMixin,
                                        SelectPluginComponent,
                                        ApertureSubsetSelectMixin,
                                        ApertureSubsetSelect,
                                        AddResultsMixin,
                                        skip_if_no_updates_since_last_active,
                                        with_spinner, with_temp_disable)
from jdaviz.core.user_api import PluginUserApi
from jdaviz.core.region_translators import regions2aperture
from jdaviz.configs.cubeviz.plugins.parsers import _return_spectrum_with_correct_units
from jdaviz.configs.cubeviz.plugins.viewers import CubevizProfileView


__all__ = ['SpectralExtraction']

ASTROPY_LT_5_3_2 = Version(astropy.__version__) < Version('5.3.2')


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
    * ``aperture`` (:class:`~jdaviz.core.template_mixin.SubsetSelect`):
      Subset to use for the spectral extraction, or ``Entire Cube``.
    * ``add_results`` (:class:`~jdaviz.core.template_mixin.AddResults`)
    * :meth:`collapse`
    * ``wavelength_dependent``:
      When true, the cone_aperture method will be used to determine the mask.
    * ``reference_spectral_value``:
      The wavelength that will be used to calculate the radius of the cone through the cube.
    * ``aperture_method`` (:class:`~jdaviz.core.template_mixin.SelectPluginComponent`):
      Extract spectrum using an aperture masking method in place of the subset mask.
    """
    template_file = __file__, "spectral_extraction.vue"
    uses_active_status = Bool(True).tag(sync=True)
    show_live_preview = Bool(True).tag(sync=True)

    # feature flag for background cone support
    dev_bg_support = Bool(False).tag(sync=True)  # when enabling: add entries to docstring

    active_step = Unicode().tag(sync=True)

    wavelength_dependent = Bool(False).tag(sync=True)
    reference_spectral_value = FloatHandleEmpty().tag(sync=True)
    slice_spectral_value = Float().tag(sync=True)

    bg_items = List([]).tag(sync=True)
    bg_selected = Any('').tag(sync=True)
    bg_selected_validity = Dict().tag(sync=True)
    bg_scale_factor = Float(1).tag(sync=True)
    bg_wavelength_dependent = Bool(False).tag(sync=True)

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

        # TODO: in the future this could be generalized with support in SelectPluginComponent
        self.aperture._default_text = 'Entire Cube'
        self.aperture._manual_options = ['Entire Cube']
        self.aperture.items = [{"label": "Entire Cube"}]
        self.aperture.select_default()

        self.background = ApertureSubsetSelect(self,
                                               'bg_items',
                                               'bg_selected',
                                               'bg_selected_validity',
                                               'bg_scale_factor',
                                               dataset='dataset',
                                               multiselect=None,
                                               default_text='None')

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

        if ASTROPY_LT_5_3_2:
            self.disabled_msg = "Spectral Extraction in Cubeviz requires astropy>=5.3.2"

        if self.app.state.settings.get('server_is_remote', False):
            # when the server is remote, saving the file in python would save on the server, not
            # on the user's machine, so export support in cubeviz should be disabled
            self.export_enabled = False

        self.disabled_msg = (
            "Spectral Extraction requires a single dataset to be loaded into Cubeviz, "
            "please load data to enable this plugin."
        )

    @property
    def user_api(self):
        expose = ['function', 'spatial_subset', 'aperture',
                  'add_results', 'collapse_to_spectrum',
                  'wavelength_dependent', 'reference_spectral_value',
                  'aperture_method']
        if self.dev_bg_support:
            expose += ['background', 'bg_wavelength_dependent']

        return PluginUserApi(self, expose=expose)

    @property
    @deprecated(since="3.9", alternative="aperture")
    def spatial_subset(self):
        return self.user_api.aperture

    @observe('active_step')
    def _active_step_changed(self, *args):
        self.aperture._set_mark_visiblities(self.active_step in ('', 'ap', 'ext'))
        self.background._set_mark_visiblities(self.active_step == 'bg')

    @property
    def slice_plugin(self):
        return self.app._jdaviz_helper.plugins['Slice']

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

    @with_spinner()
    def collapse_to_spectrum(self, add_data=True, **kwargs):
        """
        Collapse over the spectral axis.

        Parameters
        ----------
        add_data : bool
            Whether to load the resulting data back into the application according to
            ``add_results``.
        kwargs : dict
            Additional keyword arguments passed to the NDDataArray collapse operation.
            Examples include ``propagate_uncertainties`` and ``operation_ignores_mask``.
        """
        if self.conflicting_aperture_and_function:
            raise ValueError(self.conflicting_aperture_error_message)

        spectral_cube = self._app._jdaviz_helper._loaded_flux_cube
        uncert_cube = self._app._jdaviz_helper._loaded_uncert_cube
        uncertainties = None
        selected_func = self.function_selected.lower()

        # This plugin collapses over the *spatial axes* (optionally over a spatial subset,
        # defaults to ``No Subset``). Since the Cubeviz parser puts the fluxes
        # and uncertainties in different glue Data objects, we translate the spectral
        # cube and its uncertainties into separate NDDataArrays, then combine them:
        if self.aperture.selected != self.aperture.default_text:
            nddata = spectral_cube.get_subset_object(
                subset_id=self.aperture.selected, cls=NDDataArray
            )
            if uncert_cube:
                uncertainties = uncert_cube.get_subset_object(
                    subset_id=self.aperture.selected, cls=StdDevUncertainty
                )
            # Exact slice mask of cone or cylindrical aperture through the cube. `shape_mask` is
            # a 3D array with fractions of each pixel within an aperture at each
            # wavelength, on the range [0, 1].
            shape_mask = self.get_aperture()

            if self.aperture_method_selected.lower() == 'center':
                flux = nddata.data << nddata.unit
            else:  # exact (min/max not allowed here)
                # Apply the fractional pixel array to the flux cube
                flux = (shape_mask * nddata.data) << nddata.unit
            # Boolean cube which is True outside of the aperture
            # (i.e., the numpy boolean mask convention)
            mask = np.isclose(shape_mask, 0)
        else:
            nddata = spectral_cube.get_object(cls=NDDataArray)
            if uncert_cube:
                uncertainties = uncert_cube.get_object(cls=StdDevUncertainty)
            flux = nddata.data << nddata.unit
            mask = nddata.mask
        # Use the spectral coordinate from the WCS:
        if '_orig_spec' in spectral_cube.meta:
            wcs = spectral_cube.meta['_orig_spec'].wcs.spectral
        else:
            wcs = spectral_cube.coords.spectral

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
                             np.sum(shape_mask, axis=spatial_axes)) << nddata_reshaped.unit
            # Combine that information into a new NDDataArray
            collapsed_nddata = NDDataArray(flux_for_mean, mask=collapsed_as_mean.mask,
                                           uncertainty=collapsed_as_mean.uncertainty,
                                           wcs=collapsed_as_mean.wcs,
                                           meta=collapsed_as_mean.meta)
        else:
            collapsed_nddata = getattr(nddata_reshaped, selected_func)(
                axis=spatial_axes, **kwargs
            )  # returns an NDDataArray

        # Convert to Spectrum1D, with the spectral axis in correct units:
        if hasattr(spectral_cube.coords, 'spectral_wcs'):
            target_wave_unit = spectral_cube.coords.spectral_wcs.world_axis_units[0]
        else:
            target_wave_unit = spectral_cube.coords.spectral.world_axis_units[0]

        flux = collapsed_nddata.data << collapsed_nddata.unit
        mask = collapsed_nddata.mask
        uncertainty = collapsed_nddata.uncertainty

        collapsed_spec = _return_spectrum_with_correct_units(
            flux, wcs, collapsed_nddata.meta, 'flux',
            target_wave_unit=target_wave_unit,
            uncertainty=uncertainty,
            mask=mask
        )
        # stuff for exporting to file
        self.extracted_spec = collapsed_spec
        self.extracted_spec_available = True
        fname_label = self.dataset_selected.replace("[", "_").replace("]", "")
        self.filename = f"extracted_{selected_func}_{fname_label}.fits"

        # per https://jwst-docs.stsci.edu/jwst-near-infrared-camera/nircam-performance/nircam-absolute-flux-calibration-and-zeropoints # noqa
        pix_scale_factor = self.aperture.scale_factor * spectral_cube.meta.get('PIXAR_SR', 1.0)
        collapsed_spec.meta['_pixel_scale_factor'] = pix_scale_factor

        if add_data:
            self.add_results.add_results_from_plugin(
                collapsed_spec, label=self.results_label, replace=False
            )

            snackbar_message = SnackbarMessage(
                "Spectrum extracted successfully.",
                color="success",
                sender=self)
            self.hub.broadcast(snackbar_message)

        return collapsed_spec

    def get_aperture(self):
        # Retrieve flux cube and create an array to represent the cone mask
        flux_cube = self._app._jdaviz_helper._loaded_flux_cube.get_object(cls=Spectrum1D,
                                                                          statistic=None)
        # TODO: Replace with code for retrieving display_unit in cubeviz when it is available
        display_unit = flux_cube.spectral_axis.unit

        # Center is reverse coordinates
        center = (self.aperture.selected_spatial_region.center.y,
                  self.aperture.selected_spatial_region.center.x)
        aperture = regions2aperture(self.aperture.selected_spatial_region)
        aperture.positions = center

        im_shape = (flux_cube.shape[0], flux_cube.shape[1])
        aper_method = self.aperture_method_selected.lower()
        if self.wavelength_dependent:
            # Cone aperture
            if display_unit.physical_type != 'length':
                raise ValueError(
                    f'Spectral axis unit physical type is {display_unit.physical_type}, '
                    'must be length for cone aperture')

            fac = flux_cube.spectral_axis.value / self.reference_spectral_value

            # TODO: Use flux_cube.spectral_axis.to_value(display_unit) when we have unit conversion.
            if isinstance(aperture, CircularAperture):
                radii = fac * aperture.r  # radius
            elif isinstance(aperture, EllipticalAperture):
                radii = fac * aperture.a  # semimajor axis
                radii_b = fac * aperture.b  # semiminor axis
            elif isinstance(aperture, RectangularAperture):
                radii = fac * aperture.w  # full width
                radii_h = fac * aperture.h  # full height
            else:
                raise NotImplementedError(f"{aperture.__class__.__name__} is not supported")

            mask_weights = np.zeros(flux_cube.shape, dtype=np.float32)

            # Loop through cube and create cone aperture at each wavelength. Then convert that to a
            # weight array using the selected aperture method, and add it to a weight cube.
            for index, cone_r in enumerate(radii):
                if isinstance(aperture, CircularAperture):
                    aperture.r = cone_r
                elif isinstance(aperture, EllipticalAperture):
                    aperture.a = cone_r
                    aperture.b = radii_b[index]
                else:  # RectangularAperture
                    aperture.w = cone_r
                    aperture.h = radii_h[index]

                slice_mask = aperture.to_mask(method=aper_method).to_image(im_shape)
                # Add slice mask to fractional pixel array
                mask_weights[:, :, index] = slice_mask
        else:
            # Cylindrical aperture
            slice_mask = aperture.to_mask(method=aper_method).to_image(im_shape)
            # Turn 2D slice_mask into 3D array that is the same shape as the flux cube
            mask_weights = np.stack([slice_mask] * len(flux_cube.spectral_axis), axis=2)
        return mask_weights

    def vue_spectral_extraction(self, *args, **kwargs):
        self.collapse_to_spectrum(add_data=True)

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

    @observe('aperture_selected')
    def _set_default_results_label(self, event={}):
        label = "Spectral extraction"

        if (
            hasattr(self, 'aperture') and
            self.aperture.selected != self.aperture.default_text
        ):
            label += f' ({self.aperture_selected})'
        self.results_label_default = label

    @property
    def marks(self):
        marks = {}
        for id, viewer in self.app._viewer_store.items():
            if not isinstance(viewer, CubevizProfileView):
                continue
            for mark in viewer.figure.marks:
                if isinstance(mark, SpectralExtractionPreview):
                    marks[id] = mark
                    break
            else:
                mark = SpectralExtractionPreview(viewer, visible=self.is_active)
                viewer.figure.marks = viewer.figure.marks + [mark]
                marks[id] = mark
        return marks

    def _clear_marks(self):
        for mark in self.marks.values():
            if mark.visible:
                mark.clear()
                mark.visible = False

    @observe('is_active', 'show_live_preview')
    def _toggle_marks(self, event={}):
        visible = self.show_live_preview and self.is_active

        if not visible:
            self._clear_marks()
        elif event.get('name', '') in ('is_active', 'show_live_preview'):
            # then the marks themselves need to be updated
            self._live_update(event)

    @observe('aperture_selected', 'function_selected',
             'wavelength_dependent', 'reference_spectral_value',
             'aperture_method_selected',
             'previews_temp_disabled')
    @skip_if_no_updates_since_last_active()
    @with_temp_disable(timeout=0.3)
    def _live_update(self, event={}):
        if not self.show_live_preview or not self.is_active:
            self._clear_marks()
            return

        if event.get('name', '') not in ('is_active', 'show_live_preview'):
            # mark visibility hasn't been handled yet
            self._toggle_marks()

        try:
            sp = self.collapse_to_spectrum(add_data=False)
        except Exception:
            self._clear_marks()
            return

        for mark in self.marks.values():
            mark.update_xy(sp.spectral_axis.value, sp.flux.value)
            mark.visible = True

    def translate_units(self, collapsed_spec):
        # remove sr
        if u.sr in collapsed_spec._unit.bases:
            collapsed_spec._data *= collapsed_spec.meta['_pixel_scale_factor']
            collapsed_spec._unit *= u.sr
        # add sr
        elif u.sr not in collapsed_spec._unit.bases:
            collapsed_spec._data /= collapsed_spec.meta['_pixel_scale_factor']
            collapsed_spec._unit /= u.sr
