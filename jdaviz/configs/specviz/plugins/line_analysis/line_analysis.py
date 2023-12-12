import os
import logging

import numpy as np
from glue.core.message import (SubsetDeleteMessage,
                               SubsetUpdateMessage)
from glue_jupyter.common.toolbar_vuetify import read_icon
from traitlets import Bool, List, Float, Unicode, observe
from astropy import units as u
from specutils import analysis, Spectrum1D

from jdaviz.core.events import (AddDataMessage,
                                RemoveDataMessage,
                                SpectralMarksChangedMessage,
                                LineIdentifyMessage,
                                RedshiftMessage,
                                GlobalDisplayUnitChanged,
                                SnackbarMessage)
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin,
                                        DatasetSelectMixin,
                                        SpectralSubsetSelectMixin,
                                        DatasetSpectralSubsetValidMixin,
                                        SubsetSelect,
                                        SpectralContinuumMixin,
                                        SPATIAL_DEFAULT_TEXT,
                                        skip_if_no_updates_since_last_active,
                                        with_spinner)
from jdaviz.core.user_api import PluginUserApi
from jdaviz.core.tools import ICON_DIR


__all__ = ['LineAnalysis']

FUNCTIONS = {"Line Flux": analysis.line_flux,
             "Equivalent Width": analysis.equivalent_width,
             "Gaussian Sigma Width": analysis.gaussian_sigma_width,
             "Gaussian FWHM": analysis.gaussian_fwhm,
             "Centroid": analysis.centroid}


def _coerce_unit(quantity):
    """
    coerce the unit on a quantity to have a single length unit (will take the first length
    unit with a power of 1) and to strip any constants from the units.
    """
    # for some reason, quantity.unit.powers gives floats which then raise an error in
    # quantity.to and we want to avoid casting to integer in case of fractional powers
    unit = u.Unit(str(quantity.unit))
    unit_types = [str(subunit.physical_type) for subunit in unit.bases]
    length_inds = [ind for ind, (base, power, unit_type)
                   in enumerate(zip(unit.bases, unit.powers, unit_types))
                   if unit_type == 'length' and abs(power) == 1]
    # we want to force all length units (not area) to use the same base unit so they can
    # combine/cancel appropriately
    coerced_bases = [unit.bases[i if i not in length_inds else length_inds[0]]
                     for i in range(len(unit.bases))]
    coerced_unit_string = ' * '.join([f'{base}**{power}'
                                      for base, power in zip(coerced_bases, unit.powers)])
    coerced_quantity = quantity.to(coerced_unit_string)
    if getattr(quantity, 'uncertainty', None) is not None:
        coerced_quantity.uncertainty = quantity.uncertainty.to(coerced_unit_string)
    return coerced_quantity


@tray_registry('specviz-line-analysis', label="Line Analysis", viewer_requirements='spectrum')
class LineAnalysis(PluginTemplateMixin, DatasetSelectMixin, SpectralSubsetSelectMixin,
                   DatasetSpectralSubsetValidMixin, SpectralContinuumMixin):
    """
    The Line Analysis plugin returns specutils analysis for a single spectral line.
    See the :ref:`Line Analysis Plugin Documentation <line-analysis>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.close_in_tray`
    * ``dataset`` (:class:`~jdaviz.core.template_mixin.DatasetSelect`):
      Dataset to use for computing line statistics.
    * ``spatial_subset`` (:class:`~jdaviz.core.template_mixin.SubsetSelect`):
      Select which region's collapsed spectrum to analyze or ``Entire Cube``.
    * ``spectral_subset`` (:class:`~jdaviz.core.template_mixin.SubsetSelect`):
      Subset to use for the line, or ``Entire Spectrum``.
    * ``continuum`` (:class:`~jdaviz.core.template_mixin.SubsetSelect`):
      Subset to use for the continuum, or ``Surrounding`` to use a region surrounding the
      subset set in ``spectral_subset``.
    * ```continuum_width``:
      Width, relative to the overall line spectral region, to fit the linear continuum
      (excluding the region containing the line). If 1, will use endpoints within line region
      only.
    * :meth:`get_results`

    """
    dialog = Bool(False).tag(sync=True)
    template_file = __file__, "line_analysis.vue"
    uses_active_status = Bool(True).tag(sync=True)

    spatial_subset_items = List().tag(sync=True)
    spatial_subset_selected = Unicode().tag(sync=True)

    results_computing = Bool(False).tag(sync=True)
    results = List().tag(sync=True)
    results_centroid = Float().tag(sync=True)  # stored in AA units
    line_items = List([]).tag(sync=True)
    sync_identify = Bool(True).tag(sync=True)
    sync_identify_icon_enabled = Unicode(read_icon(os.path.join(ICON_DIR, 'line_select.svg'), 'svg+xml')).tag(sync=True)  # noqa
    sync_identify_icon_disabled = Unicode(read_icon(os.path.join(ICON_DIR, 'line_select_disabled.svg'), 'svg+xml')).tag(sync=True)  # noqa
    identified_line = Unicode("").tag(sync=True)
    selected_line = Unicode("").tag(sync=True)
    selected_line_redshift = Float(0).tag(sync=True)

    def __init__(self, *args, **kwargs):

        super().__init__(**kwargs)

        self.update_results(None)

        # when accessing the selected data, access the spectrum-viewer version
        self.dataset._viewers = [self._default_spectrum_viewer_reference_name]
        # require entries to be in spectrum-viewer (not other cubeviz images, etc)
        self.dataset.add_filter('layer_in_spectrum_viewer')

        # continuum selection is mandatory for line-analysis
        self._continuum_remove_none_option()

        if self.app.state.settings.get("configuration") == "cubeviz":
            self.spatial_subset = SubsetSelect(self,
                                               'spatial_subset_items',
                                               'spatial_subset_selected',
                                               default_text=SPATIAL_DEFAULT_TEXT,
                                               filters=['is_spatial'])
        else:
            self.spatial_subset = None

        self.hub.subscribe(self, AddDataMessage,
                           handler=self._on_viewer_data_changed)
        self.hub.subscribe(self, RemoveDataMessage,
                           handler=self._on_viewer_data_changed)

        self.hub.subscribe(self, SubsetDeleteMessage,
                           handler=self._on_viewer_subsets_changed)
        self.hub.subscribe(self, SubsetUpdateMessage,
                           handler=self._on_viewer_subsets_changed)
        self.hub.subscribe(self, SpectralMarksChangedMessage,
                           handler=self._on_plotted_lines_changed)
        self.hub.subscribe(self, LineIdentifyMessage,
                           handler=self._on_identified_line_changed)
        self.hub.subscribe(self, GlobalDisplayUnitChanged,
                           handler=self._on_global_display_unit_changed)

    @property
    def _default_spectrum_viewer_reference_name(self):
        return getattr(
            self.app._jdaviz_helper, '_default_spectrum_viewer_reference_name', 'spectrum-viewer'
        )

    # backwards compatibility for width (replace with user API deprecation)
    @property
    def width(self):
        logging.warning(f"DeprecationWarning: width was replaced by continuum_width in 3.9 and will be removed in a future release")  # noqa
        return self.continuum_width

    @width.setter
    def width(self, width):
        logging.warning("DeprecationWarning: width was replaced by continuum_width in 3.9 and will be removed in a future release")  # noqa
        self.continuum_width = width

    @property
    def user_api(self):
        # deprecated: width was replaced with continuum_width in 3.9 so should be removed from the
        # user API and the property and setter above as soon as 3.11.
        return PluginUserApi(self, expose=('dataset', 'spatial_subset', 'spectral_subset',
                                           'continuum', 'width', 'continuum_width', 'get_results'))

    def _on_viewer_data_changed(self, msg):
        viewer_id = self.app._viewer_item_by_reference(
            self._default_spectrum_viewer_reference_name
        ).get('id')
        if msg is None or msg.viewer_id != viewer_id or msg.data is None:
            return

        viewer = self.app.get_viewer(self._default_spectrum_viewer_reference_name)
        viewer_data_labels = [layer.layer.label for layer in viewer.layers]
        if msg.data.label not in viewer_data_labels:
            return

        get_data_kwargs = {'data_label': msg.data.label}
        if self.config == 'cubeviz':
            get_data_kwargs['function'] = getattr(viewer.state, 'function', None)
        viewer_data = self.app._jdaviz_helper.get_data(**get_data_kwargs)

        # If no data is currently plotted, don't attempt to update
        if viewer_data is None:
            self.disabled_msg = 'Line Analysis unavailable without spectral data'
            return

        if viewer_data.spectral_axis.unit == u.pix:
            # disable the plugin until we can address this properly (either using the wavelength
            # solution to support pixels in line-lists, or properly displaying the extracted
            # 1d spectrum in wavelength-space)
            self.disabled_msg = 'Line Analysis unavailable when x-axis is in pixels'
        else:
            self.disabled_msg = ''

    def _on_viewer_subsets_changed(self, msg):
        """
        Update the statistics if any of the referenced regions have changed

        Parameters
        ----------
        msg : `glue.core.Message`
            The glue message passed to this callback method.
        """
        if (msg.subset.label in [self.spectral_subset_selected,
                                 self.spatial_subset_selected,
                                 self.continuum_subset_selected]):
            self._calculate_statistics(msg)

    def _on_global_display_unit_changed(self, msg):
        self._calculate_statistics(msg)

    @observe('is_active')
    def _is_active_changed(self, msg):
        if self.disabled_msg:
            return

        for pos, mark in self.continuum_marks.items():
            mark.visible = self.is_active
        self._calculate_statistics(msg)

    def update_results(self, results=None):
        if results is None:
            self.results = [{'function': function, 'result': ''} for function in FUNCTIONS]
            self._update_continuum_marks()
        else:
            self.results = results

    def get_results(self):
        # user-facing API call to force updating and retrieving results, even if the plugin
        # is closed

        if not self.spectral_subset_valid:
            valid, spec_range, subset_range = self._check_dataset_spectral_subset_valid(return_ranges=True)  # noqa
            raise ValueError(f"spectral subset '{self.spectral_subset.selected}' {subset_range} is outside data range of '{self.dataset.selected}' {spec_range}")  # noqa

        self._calculate_statistics()
        return self.results

    def _on_plotted_lines_changed(self, msg):
        self.line_marks = msg.marks
        self.line_items = msg.names_rest
        if self.selected_line not in self.line_items:
            # default to identified line if available
            self.selected_line = self.identified_line

    def _on_identified_line_changed(self, msg):
        self.identified_line = msg.name_rest
        if self.sync_identify or not self.selected_line:
            # then we should follow the identified line, either because of sync
            # or because nothing has been selected yet.
            # if results aren't available yet, then we'll wait until they are
            # in which case we'll default to the identified line
            self.selected_line = self.identified_line

    @observe("dataset_selected", "spatial_subset_selected", "spectral_subset_selected",
             "continuum_subset_selected", "continuum_width")
    @skip_if_no_updates_since_last_active()
    @with_spinner('results_computing')
    def _calculate_statistics(self, msg={}):
        """
        Run the line analysis functions on the selected data/subset and
        display the results.
        """
        if not hasattr(self, 'dataset') or self.app._jdaviz_helper is None:  # noqa
            # during initial init, this can trigger before the component is initialized
            return

        if self.disabled_msg != '':
            self.update_results(None)
            return

        # call directly since this observe may be triggered before the spectral_subset_valid
        # traitlet is updated
        if not self._check_dataset_spectral_subset_valid():
            # skip gracefully, if the user called from get_results, and error would be raised there
            self.update_results(None)
            return

        spectrum, continuum, spec_subtracted = self._get_continuum(self.dataset,
                                                                   self.spatial_subset,
                                                                   self.spectral_subset,
                                                                   update_marks=True)
        if spectrum is None:
            self.update_results(None)
            return

        def _uncertainty(result):
            if getattr(result, 'uncertainty', None) is not None:
                # we'll keep the uncertainty and result in the same unit (so
                # we only have to show the unit at the end)
                if np.isnan(result.uncertainty.value) or np.isinf(result.uncertainty.value):
                    return ''
                return str(result.uncertainty.to_value(result.unit))
            else:
                return ''

        temp_results = []

        if spec_subtracted.mask is not None:
            # temporary fix while mask may contain None:
            spec_subtracted.mask = spec_subtracted.mask.astype(bool)

        for function in FUNCTIONS:
            # TODO: update specutils to allow ALL analysis to take regions and continuum so we
            # don't need these if statements
            if function == "Line Flux":
                flux_unit = spec_subtracted.flux.unit
                # If the flux unit is equivalent to Jy, or Jy per spaxel for Cubeviz,
                # enforce integration in frequency space
                if (flux_unit.is_equivalent(u.Jy) or
                        flux_unit.is_equivalent(u.Jy/u.sr)):
                    # Perform integration in frequency space
                    freq_spec = Spectrum1D(
                        spectral_axis=spec_subtracted.spectral_axis.to(u.Hz,
                                                                       equivalencies=u.spectral()),
                        flux=spec_subtracted.flux,
                        uncertainty=spec_subtracted.uncertainty)

                    try:
                        raw_result = analysis.line_flux(freq_spec)
                    except ValueError as e:
                        # can happen if interpolation out-of-bounds or any error from specutils
                        # let's avoid the whole app crashing and instead expose the error to the
                        # user
                        self.hub.broadcast(SnackbarMessage(
                            f"failed to calculate line analysis statistics: {e}", sender=self,
                            color="warning"))
                        self.update_results(None)
                        return

                    # When flux is equivalent to Jy, lineflux result should be shown in W/m2
                    if flux_unit.is_equivalent(u.Jy/u.sr):
                        final_unit = u.Unit('W/(m2 sr)')
                    else:
                        final_unit = u.Unit('W/m2')

                    temp_result = raw_result.to(final_unit)
                    if getattr(raw_result, 'uncertainty', None) is not None:
                        temp_result.uncertainty = raw_result.uncertainty.to(final_unit)

                # If the flux unit is instead equivalent to power density
                # (Jy, but defined in wavelength), enforce integration in wavelength space
                elif (flux_unit.is_equivalent(u.Unit('W/(m2 m)')) or
                        flux_unit.is_equivalent(u.Unit('W/(m2 m sr)'))):
                    # Perform integration in wavelength space using MKS unit (meters)
                    wave_spec = Spectrum1D(
                        spectral_axis=spec_subtracted.spectral_axis.to(u.m,
                                                                       equivalencies=u.spectral()),
                        flux=spec_subtracted.flux,
                        uncertainty=spec_subtracted.uncertainty)
                    try:
                        raw_result = analysis.line_flux(wave_spec)
                    except ValueError as e:
                        # can happen if interpolation out-of-bounds or any error from specutils
                        # let's avoid the whole app crashing and instead expose the error to the
                        # user
                        self.hub.broadcast(SnackbarMessage(
                            f"failed to calculate line analysis statistics: {e}", sender=self,
                            color="warning"))
                        self.update_results(None)
                        return
                    # When flux is equivalent to Jy, lineflux result should be shown in W/m2
                    if flux_unit.is_equivalent(u.Unit('W/(m2 m)'/u.sr)):
                        final_unit = u.Unit('W/(m2 sr)')
                    else:
                        final_unit = u.Unit('W/m2')

                    temp_result = raw_result.to(final_unit)
                    if getattr(raw_result, 'uncertainty', None) is not None:
                        temp_result.uncertainty = raw_result.uncertainty.to(final_unit)

                # Otherwise, just rely on the default specutils line_flux result
                else:
                    temp_result = analysis.line_flux(spec_subtracted)

            elif function == "Equivalent Width":
                if np.any(continuum <= 0):
                    temp_results.append({'function': function,
                                         'result': '',
                                         'error_msg': 'N/A (continuum <= 0)',
                                         'uncertainty': '',
                                         'unit': ''})
                    continue
                else:
                    spec_normalized = spectrum / continuum
                    if spec_normalized.mask is not None:
                        spec_normalized.mask = spec_normalized.mask.astype(bool)

                    temp_result = FUNCTIONS[function](spec_normalized)
            elif function == "Centroid":
                # TODO: update specutils to be consistent with region vs regions and default to
                # regions=None so this elif can be removed
                temp_result = FUNCTIONS[function](spec_subtracted, region=None)
                self.results_centroid = temp_result.to_value(u.AA, equivalencies=u.spectral())
            else:
                # if the minimum flux is negative, translate the spectrum until it is
                # non-negative for the these line analysis functions:
                if spec_subtracted.flux.min() < 0:
                    spec_subtracted_nonneg_flux = (
                            spec_subtracted - np.min((spectrum - continuum).flux)
                    )
                else:
                    spec_subtracted_nonneg_flux = spec_subtracted
                temp_result = FUNCTIONS[function](spec_subtracted_nonneg_flux)

            temp_result = _coerce_unit(temp_result)
            temp_results.append({'function': function,
                                 'result': str(temp_result.value),
                                 'uncertainty': _uncertainty(temp_result),
                                 'unit': str(temp_result.unit)})

        if not self.selected_line and self.identified_line:
            # default to the identified line
            self.selected_line = self.identified_line

        self.update_results(temp_results)

    def _compute_redshift_for_selected_line(self):
        index = self.line_items.index(self.selected_line)
        line_mark = self.line_marks[index]
        rest_value = (line_mark.rest_value * line_mark.xunit).to_value(u.AA,
                                                                       equivalencies=u.spectral())
        return (self.results_centroid - rest_value) / rest_value

    @observe('sync_identify')
    def _sync_identify_changed(self, event={}):
        if not event.get('new', self.sync_identify):
            return

        if not self.identified_line and self.selected_line:
            # then we just enabled the sync, but no line is currently
            # identified, so we'll identify the current selection
            msg = LineIdentifyMessage(self.selected_line, sender=self)
            self.hub.broadcast(msg)
        elif self.identified_line:
            # then update the selection the the identified line
            self.selected_line = self.identified_line

    @observe('selected_line')
    def _selected_line_changed(self, event):
        if self.sync_identify:
            msg = LineIdentifyMessage(event.get('new', self.selected_line), sender=self)
            self.hub.broadcast(msg)

    @observe('results_centroid', 'selected_line')
    def _update_selected_line_redshift(self, event):
        if self.selected_line and self.results_centroid is not None:
            # compute redshift that WILL be applied if clicking assign
            self.selected_line_redshift = self._compute_redshift_for_selected_line()

    def vue_line_assign(self, msg=None):
        z = self._compute_redshift_for_selected_line()
        msg = RedshiftMessage('redshift', z, sender=self)
        self.hub.broadcast(msg)
