from packaging.version import Version
import numpy as np
import astropy
import astropy.units as u
from astropy.nddata import (
    NDDataArray, StdDevUncertainty, NDUncertainty
)
from traitlets import List, Unicode, observe

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin,
                                        SelectPluginComponent,
                                        SpatialSubsetSelectMixin,
                                        AddResultsMixin,
                                        with_spinner)
from jdaviz.core.user_api import PluginUserApi
from jdaviz.configs.cubeviz.plugins.parsers import _return_spectrum_with_correct_units

__all__ = ['SpectralExtraction']

ASTROPY_LT_5_3_2 = Version(astropy.__version__) < Version('5.3.2')


@tray_registry(
    'cubeviz-spectral-extraction', label="Spectral Extraction", viewer_requirements='spectrum'
)
class SpectralExtraction(PluginTemplateMixin, SpatialSubsetSelectMixin, AddResultsMixin):
    """
    See the :ref:`Spectral Extraction Plugin Documentation <spex>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.close_in_tray`
    * ``spatial_subset`` (:class:`~jdaviz.core.template_mixin.SubsetSelect`):
      Subset to use for the spectral extraction, or ``No Subset``.
    * ``add_results`` (:class:`~jdaviz.core.template_mixin.AddResults`)
    * :meth:`collapse`
    """
    template_file = __file__, "spectral_extraction.vue"
    function_items = List().tag(sync=True)
    function_selected = Unicode('Sum').tag(sync=True)

    def __init__(self, *args, **kwargs):

        self._default_spectrum_viewer_reference_name = kwargs.get(
            "spectrum_viewer_reference_name", "spectrum-viewer"
        )

        super().__init__(*args, **kwargs)

        self.function = SelectPluginComponent(
            self,
            items='function_items',
            selected='function_selected',
            manual_options=['Mean', 'Min', 'Max', 'Sum']
        )
        self._set_default_results_label()
        self.add_results.viewer.filters = ['is_spectrum_viewer']

        if ASTROPY_LT_5_3_2:
            self.disabled_msg = "Spectral Extraction in Cubeviz requires astropy>=5.3.2"

    @property
    def user_api(self):
        return PluginUserApi(
            self,
            expose=(
                'function', 'spatial_subset',
                'add_results', 'collapse_to_spectrum'
            )
        )

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
        # get glue Data objects for the spectral cube and uncertainties
        flux_viewer = self._app.get_viewer(
            self._app._jdaviz_helper._default_flux_viewer_reference_name
        )
        uncert_viewer = self._app.get_viewer(
            self._app._jdaviz_helper._default_uncert_viewer_reference_name
        )
        [spectral_cube] = flux_viewer.data()
        [uncert_cube] = uncert_viewer.data()

        # This plugin collapses over the *spatial axes* (optionally over a spatial subset,
        # defaults to ``No Subset``). Since the Cubeviz parser puts the fluxes
        # and uncertainties in different glue Data objects, we translate the spectral
        # cube and its uncertainties into separate NDDataArrays, then combine them:
        if self.spatial_subset_selected != self.spatial_subset.default_text:
            nddata = spectral_cube.get_subset_object(
                subset_id=self.spatial_subset_selected, cls=NDDataArray
            )
            uncertainties = uncert_cube.get_subset_object(
                subset_id=self.spatial_subset_selected, cls=StdDevUncertainty
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

    @observe('spatial_subset_selected')
    def _set_default_results_label(self, event={}):
        label = "Spectral extraction"

        if (
            hasattr(self, 'spatial_subset') and
            self.spatial_subset.selected != self.spatial_subset.default_text
        ):
            label += f' ({self.spatial_subset_selected})'
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
