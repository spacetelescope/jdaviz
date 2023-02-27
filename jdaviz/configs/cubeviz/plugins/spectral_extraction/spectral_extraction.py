from astropy.nddata import NDDataArray, StdDevUncertainty
from astropy.wcs.wcsapi.fitswcs import SlicedFITSWCS
from glue_astronomy.translators.spectrum1d import PaddedSpectrumWCS
from traitlets import List, Unicode

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin,
                                        SelectPluginComponent,
                                        SpatialSubsetSelectMixin,
                                        AddResultsMixin)
from jdaviz.core.user_api import PluginUserApi

__all__ = ['SpectralExtraction']


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

        self._label_counter = 0

        self.function = SelectPluginComponent(self,
                                              items='function_items',
                                              selected='function_selected',
                                              manual_options=['Mean', 'Min', 'Max', 'Sum'])  # noqa

        self.add_results.viewer.filters = ['is_spectrum_viewer']

    @property
    def user_api(self):
        return PluginUserApi(self, expose=('function', 'spatial_subset',
                                           'add_results', 'collapse_to_spectrum'))

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
            Examples include ``propagate_uncertainties`` and ``ignore_masked_data``.
        """
        # get glue Data objects for the spectral cube and uncertainties
        [spectral_cube] = self._app.get_data_from_viewer(
            self._app._jdaviz_helper._default_flux_viewer_reference_name,
            include_subsets=False
        ).values()
        [uncert_cube] = self._app.get_data_from_viewer(
            self._app._jdaviz_helper._default_uncert_viewer_reference_name,
            include_subsets=False
        ).values()

        # This plugin collapses over the *spatial axes* (optionally over a spatial subset,
        # defaults to ``No Subset``). Since the Cubeviz parser puts the fluxes
        # and uncertainties in different glue Data objects, we translate the spectral
        # cube and its uncertainties into separate NDDataArrays, then combine them:
        if self.spatial_subset_selected != self.spatial_subset.default_text:
            nddata = spectral_cube.get_subset_object(
                subset_id=self.spatial_subset_selected, cls=NDDataArray
            )
            uncertainties = uncert_cube.get_subset_object(
                subset_id=self.spatial_subset_selected, cls=NDDataArray
            ).data
        else:
            nddata = spectral_cube.get_object(cls=NDDataArray)
            uncertainties = uncert_cube.get_object(cls=NDDataArray).data

        # We attach the uncertainties to the NDDataArray with the data:
        nddata.uncertainty = StdDevUncertainty(uncertainties)

        # Collapse an e.g. 3D spectral cube to 1D spectrum, assuming that last axis
        # is always wavelength. This will need adjustment after the following
        # specutils PR is merged: https://github.com/astropy/specutils/pull/999
        spatial_axes = tuple(range(nddata.ndim - 1))

        # by default we want to use ignore_masked_data=True in nddata:
        if "ignore_masked_data" not in kwargs:
            kwargs["ignore_masked_data"] = True
        # by default we want to propagate uncertainties:
        if "propagate_uncertainties" not in kwargs:
            kwargs["propagate_uncertainties"] = True

        collapsed_spec = getattr(nddata, self.function_selected.lower())(
            axis=spatial_axes, **kwargs
        )  # returns an NDDataArray

        # Hack to extract the spectral axis with units converted
        # to the wavelength axis in specviz:
        collapsed_spec.wcs = None
        collapsed_spec.wcs = PaddedSpectrumWCS(
            SlicedFITSWCS(spectral_cube.coords, spatial_axes), 1
        )
        if add_data:
            label = f"Spectrum extracted from {self._app.data_collection[0].label}"
            self.add_results.add_results_from_plugin(collapsed_spec, label=label)

            snackbar_message = SnackbarMessage(
                "Spectrum extracted successfully.",
                color="success",
                sender=self)
            self.hub.broadcast(snackbar_message)

        return collapsed_spec

    def vue_spectral_extraction(self, *args, **kwargs):
        self.collapse_to_spectrum(add_data=True)
