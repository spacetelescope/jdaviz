import os
from pathlib import Path

from packaging.version import Version
import numpy as np
import astropy
import astropy.units as u
from astropy.utils.decorators import deprecated
from astropy.nddata import (
    NDDataArray, StdDevUncertainty, NDUncertainty
)
from traitlets import Bool, Float, List, Unicode, observe

from jdaviz.core.custom_traitlets import FloatHandleEmpty
from jdaviz.core.events import SnackbarMessage, SliceWavelengthUpdatedMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin,
                                        DatasetSelectMixin,
                                        SelectPluginComponent,
                                        ApertureSubsetSelectMixin,
                                        AddResultsMixin,
                                        with_spinner)
from jdaviz.core.user_api import PluginUserApi
from jdaviz.configs.cubeviz.plugins.parsers import _return_spectrum_with_correct_units


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
    """
    template_file = __file__, "spectral_extraction.vue"
    uses_active_status = Bool(True).tag(sync=True)

    # feature flag for cone support
    dev_cone_support = Bool(False).tag(sync=True)
    wavelength_dependent = Bool(False).tag(sync=True)
    reference_wavelength = FloatHandleEmpty().tag(sync=True)
    slice_wavelength = Float().tag(sync=True)

    function_items = List().tag(sync=True)
    function_selected = Unicode('Sum').tag(sync=True)
    filename = Unicode().tag(sync=True)
    extracted_spec_available = Bool(False).tag(sync=True)
    overwrite_warn = Bool(False).tag(sync=True)

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

        self.function = SelectPluginComponent(
            self,
            items='function_items',
            selected='function_selected',
            manual_options=['Mean', 'Min', 'Max', 'Sum']
        )
        self._set_default_results_label()
        self.add_results.viewer.filters = ['is_spectrum_viewer']

        self.session.hub.subscribe(self, SliceWavelengthUpdatedMessage,
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
        return PluginUserApi(
            self,
            expose=(
                'function', 'spatial_subset', 'aperture',
                'add_results', 'collapse_to_spectrum'
            )
        )

    @property
    @deprecated(since="3.9", alternative="aperture")
    def spatial_subset(self):
        return self.user_api.aperture

    @property
    def slice_plugin(self):
        return self.app._jdaviz_helper.plugins['Slice']

    @observe('wavelength_dependent')
    def _wavelength_dependent_changed(self, *args):
        if self.wavelength_dependent:
            self.reference_wavelength = self.slice_plugin.wavelength
        # NOTE: this can be redundant in the case where reference_wavelength changed and triggers
        # the observe, but we need to ensure it is updated if reference_wavelength is unchanged
        self._update_mark_scale()

    def _on_slice_changed(self, msg):
        self.slice_wavelength = msg.wavelength

    def vue_goto_reference_wavelength(self, *args):
        self.slice_plugin.wavelength = self.reference_wavelength

    def vue_adopt_slice_as_reference(self, *args):
        self.reference_wavelength = self.slice_plugin.wavelength

    @observe('reference_wavelength', 'slice_wavelength')
    def _update_mark_scale(self, *args):
        if not self.wavelength_dependent:
            self.aperture.scale_factor = 1.0
            return
        self.aperture.scale_factor = self.slice_wavelength/self.reference_wavelength

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
        spectral_cube = self._app._jdaviz_helper._loaded_flux_cube
        uncert_cube = self._app._jdaviz_helper._loaded_uncert_cube

        # This plugin collapses over the *spatial axes* (optionally over a spatial subset,
        # defaults to ``No Subset``). Since the Cubeviz parser puts the fluxes
        # and uncertainties in different glue Data objects, we translate the spectral
        # cube and its uncertainties into separate NDDataArrays, then combine them:
        if self.aperture.selected != self.aperture.default_text:
            nddata = spectral_cube.get_subset_object(
                subset_id=self.aperture.selected, cls=NDDataArray
            )
            uncertainties = uncert_cube.get_subset_object(
                subset_id=self.aperture.selected, cls=StdDevUncertainty
            )
        else:
            nddata = spectral_cube.get_object(cls=NDDataArray)
            uncertainties = uncert_cube.get_object(cls=StdDevUncertainty)

        # Use the spectral coordinate from the WCS:
        if '_orig_spec' in spectral_cube.meta:
            wcs = spectral_cube.meta['_orig_spec'].wcs.spectral
        else:
            wcs = spectral_cube.coords.spectral

        flux = nddata.data << nddata.unit
        mask = nddata.mask

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

        collapsed_nddata = getattr(nddata_reshaped, self.function_selected.lower())(
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
        self.filename = f"extracted_{self.function_selected.lower()}_{fname_label}.fits"

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


def _move_spectral_axis(wcs, flux, mask=None, uncertainty=None):
    """
    Move spectral axis last to match specutils convention. This
    function borrows from:
        https://github.com/astropy/specutils/blob/
        6eb7f96498072882c97763d4cd10e07cf81b6d33/specutils/spectra/spectrum1d.py#L185-L225
    """
    naxis = getattr(wcs, 'naxis', len(wcs.world_axis_physical_types))
    if naxis > 1:
        temp_axes = []
        phys_axes = wcs.world_axis_physical_types
        for i in range(len(phys_axes)):
            if phys_axes[i] is None:
                continue
            if phys_axes[i][0:2] == "em" or phys_axes[i][0:5] == "spect":
                temp_axes.append(i)
        if len(temp_axes) != 1:
            raise ValueError("Input WCS must have exactly one axis with "
                             "spectral units, found {}".format(len(temp_axes)))

        # Due to FITS conventions, a WCS with spectral axis first corresponds
        # to a flux array with spectral axis last.
        if temp_axes[0] != 0:
            wcs = wcs.swapaxes(0, temp_axes[0])
            if flux is not None:
                flux = np.swapaxes(flux, len(flux.shape) - temp_axes[0] - 1, -1)
            if mask is not None:
                mask = np.swapaxes(mask, len(mask.shape) - temp_axes[0] - 1, -1)
            if uncertainty is not None:
                if isinstance(uncertainty, NDUncertainty):
                    # Account for Astropy uncertainty types
                    unc_len = len(uncertainty.array.shape)
                    temp_unc = np.swapaxes(uncertainty.array,
                                           unc_len - temp_axes[0] - 1, -1)
                    if uncertainty.unit is not None:
                        temp_unc = temp_unc * u.Unit(uncertainty.unit)
                    uncertainty = type(uncertainty)(temp_unc)
                else:
                    uncertainty = np.swapaxes(uncertainty,
                                              len(uncertainty.shape) -
                                              temp_axes[0] - 1, -1)
    return wcs, flux, mask, uncertainty
