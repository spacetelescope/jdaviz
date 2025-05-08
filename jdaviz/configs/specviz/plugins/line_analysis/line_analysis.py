import os

import numpy as np
from glue.core.message import (SubsetDeleteMessage,
                               SubsetUpdateMessage)
from glue_jupyter.common.toolbar_vuetify import read_icon
from traitlets import Bool, List, Float, Unicode, observe
from astropy import units as u
from specutils import analysis, Spectrum1D

from jdaviz.configs.specviz.plugins.viewers import Spectrum1DViewer
from jdaviz.core.events import (AddDataMessage,
                                RemoveDataMessage,
                                SpectralMarksChangedMessage,
                                LineIdentifyMessage,
                                RedshiftMessage,
                                GlobalDisplayUnitChanged,
                                ViewerAddedMessage,
                                ViewerRemovedMessage,
                                SnackbarMessage)
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin,
                                        DatasetSelectMixin,
                                        TableMixin,
                                        SpectralSubsetSelectMixin,
                                        DatasetSpectralSubsetValidMixin,
                                        SpectralContinuumMixin,
                                        with_spinner)
from jdaviz.core.user_api import PluginUserApi
from jdaviz.core.tools import ICON_DIR
from jdaviz.core.unit_conversion_utils import check_if_unit_is_per_solid_angle


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


@tray_registry('specviz-line-analysis', label="Line Analysis", category="data:analysis")
class LineAnalysis(PluginTemplateMixin, DatasetSelectMixin, TableMixin,
                   SpectralSubsetSelectMixin, DatasetSpectralSubsetValidMixin,
                   SpectralContinuumMixin):
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
    * :meth:`~jdaviz.core.template_mixin.TableMixin.export_table`

    """
    dialog = Bool(False).tag(sync=True)
    template_file = __file__, "line_analysis.vue"
    uses_active_status = Bool(True).tag(sync=True)

    results_available = Bool(False).tag(sync=True)
    results_computing = Bool(False).tag(sync=True)
    results = List().tag(sync=True)
    results_centroid = Float().tag(sync=True)  # stored in AA units
    line_menu_items = List([]).tag(sync=True)
    sync_identify = Bool(True).tag(sync=True)
    sync_identify_icon_enabled = Unicode(read_icon(os.path.join(ICON_DIR, 'line_select.svg'), 'svg+xml')).tag(sync=True)  # noqa
    sync_identify_icon_disabled = Unicode(read_icon(os.path.join(ICON_DIR, 'line_select_disabled.svg'), 'svg+xml')).tag(sync=True)  # noqa
    identified_line = Unicode("").tag(sync=True)
    selected_line = Unicode("").tag(sync=True)
    selected_line_redshift = Float(0).tag(sync=True)

    def __init__(self, *args, **kwargs):

        super().__init__(**kwargs)

        # description displayed under plugin title in tray
        self._plugin_description = 'Return statistics for spectral line.'

        self.update_results(None)

        # require entries to be in spectrum-viewer (not other cubeviz images, etc)
        self.dataset.add_filter('layer_in_spectrum_viewer')

        # continuum selection is mandatory for line-analysis
        self._continuum_remove_none_option()

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
        self.hub.subscribe(self, ViewerAddedMessage,
                           handler=self._on_viewers_changed)
        self.hub.subscribe(self, ViewerRemovedMessage,
                           handler=self._on_viewers_changed)

        stats = ['Line Flux', 'Equivalent Width', 'Gaussian Sigma Width',
                 'Gaussian FWHM', 'Centroid']
        headers = [h for stat in stats for h in [stat, f'{stat}:uncertainty', f'{stat}:unit']]
        headers += ['dataset', 'spectral_subset', 'continuum', 'continuum_width']
        self.table.headers_avail = headers
        self.table.headers_visible = [h for h in headers if ':' not in h]

        self._set_relevant()

    @observe('dataset_items')
    def _set_relevant(self, *args):
        if self.app.config == 'deconfigged':
            if not len(self.dataset_items):
                self.irrelevant_msg = 'Line Analysis unavailable without data loaded in spectrum viewer'  # noqa
            else:
                self.irrelevant_msg = ''
        else:
            sv = self.spectrum_viewer
            if sv is None:
                self.irrelevant_msg = 'Line Analysis unavailable without spectrum viewer'
            elif not len(sv.layers):
                self.irrelevant_msg = ''
                self.disabled_msg = 'Line Analysis unavailable without data loaded in spectrum viewer'  # noqa
            else:
                self.irrelevant_msg = ''
                self.disabled_msg = ''

    @property
    def user_api(self):
        return PluginUserApi(self, expose=('dataset', 'spectral_subset',
                                           'continuum', 'continuum_width', 'get_results',
                                           'export_table'))

    @property
    def line_items(self):
        # Return list of only the table indices ("name_rest" in line table) from line_menu_items
        return [item["value"] for item in self.line_menu_items]

    def _on_viewers_changed(self, msg):
        # when accessing the selected data, access the spectrum-viewer version
        self.dataset._viewers = [v.reference_id for v in self.app._viewer_store.values()
                                 if isinstance(v, Spectrum1DViewer)]

    def _on_viewer_data_changed(self, msg):
        self._set_relevant()
        if self.disabled_msg or self.irrelevant_msg:
            return

        sv = self.spectrum_viewer
        if sv is None:
            return
        viewer_id = sv.reference_id
        if msg is None or msg.viewer_id != viewer_id or msg.data is None:
            return

        viewer_data_labels = [layer.layer.label for layer in sv.layers]
        if msg.data.label not in viewer_data_labels:
            return

        viewer_data = self.app._jdaviz_helper.get_data(data_label=msg.data.label)

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

        if self.is_active:
            self._calculate_statistics(msg)

    def update_results(self, results=None):
        if results is None:
            self.results_available = False
            self.results = [{'function': function, 'result': ''} for function in FUNCTIONS]
            self._update_continuum_marks()
        else:
            self.results = results
            self.results_available = True

    def get_results(self, add_to_table=True):
        """
        Get the results of the line analysis.

        Returns
        -------
        list
            The results of the line analysis.
        """
        # user-facing API call to force updating and retrieving results, even if the plugin
        # is closed

        if not self.spectral_subset_valid:
            valid, spec_range, subset_range = self._check_dataset_spectral_subset_valid(return_ranges=True)  # noqa
            raise ValueError(f"spectral subset '{self.spectral_subset.selected}' {subset_range}"
                             f" is outside data range of '{self.dataset.selected}' {spec_range}")

        self._calculate_statistics(store_results=True)

        if add_to_table:
            result_dict = {result_item['function']: result_item['result']
                           for result_item in self.results}
            result_dict.update({result_item['function'] + ':uncertainty': result_item.get('uncertainty', '')  # noqa
                                for result_item in self.results})
            result_dict.update({result_item['function'] + ':unit': result_item.get('unit', '')
                                for result_item in self.results})
            result_dict['dataset'] = self.dataset.selected
            result_dict['spectral_subset'] = self.spectral_subset.selected
            result_dict['continuum'] = self.continuum.selected
            if self.continuum.selected == 'Surrounding' and self.spectral_subset.selected != 'Entire Spectrum':  # noqa
                result_dict['continuum_width'] = self.continuum_width
            else:
                result_dict['continuum_width'] = np.nan
            self.table.add_item(result_dict)

        return self.results

    def vue_calculate_results(self, *args):
        self.get_results(add_to_table=True)

    def _on_plotted_lines_changed(self, msg):
        self.line_marks = msg.marks
        self.line_menu_items = [{"title": f"{mark.name} {mark.rest_value} {mark.xunit}", "value": name_rest}  # noqa
                                for mark, name_rest in zip(msg.marks, msg.names_rest)]
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

    @observe("dataset_selected", "spectral_subset_selected",
             "continuum_subset_selected", "continuum_width")
    @with_spinner('results_computing')
    def _calculate_statistics(self, msg={}, store_results=False):
        """
        Run the line analysis functions on the selected data/subset and
        display the results.
        """
        if not hasattr(self, 'dataset') or self.app._jdaviz_helper is None:  # noqa
            # during initial init, this can trigger before the component is initialized
            return

        if self.disabled_msg != '' or (not store_results and not self.is_active):
            self.update_results(None)
            return

        # call directly since this observe may be triggered before the spectral_subset_valid
        # traitlet is updated
        if not self._check_dataset_spectral_subset_valid():
            # skip gracefully, if the user called from get_results, and error would be raised there
            self.update_results(None)
            return

        spectrum, continuum, spec_subtracted = self._get_continuum(self.dataset,
                                                                   self.spectral_subset,
                                                                   update_marks=True)
        if spectrum is None:
            self.update_results(None)
            return

        if not store_results:
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
                if flux_unit == u.dimensionless_unscaled:
                    add_flux = True
                    flux_unit = u.Unit(self.spectrum_viewer.state.y_display_unit)
                else:
                    add_flux = False

                solid_angle_in_flux_unit = check_if_unit_is_per_solid_angle(flux_unit,
                                                                            return_unit=True)
                if solid_angle_in_flux_unit is None:
                    # use dimensionless_unscaled as a placeholder unit.
                    # is_equivalent() checks won't pass anyway if theres no
                    # solid angle in the unit, so it won't matter what this is
                    solid_angle_in_flux_unit = u.dimensionless_unscaled

                solid_angle_string = solid_angle_in_flux_unit.to_string()

                # If the flux unit is equivalent to Jy, or Jy per spaxel for Cubeviz,
                # enforce integration in frequency space
                if (flux_unit.is_equivalent(u.Jy) or
                   flux_unit.is_equivalent(u.Jy / solid_angle_in_flux_unit)):
                    # Perform integration in frequency space
                    freq_spec = Spectrum1D(
                        spectral_axis=spec_subtracted.spectral_axis.to(u.Hz,
                                                                       equivalencies=u.spectral()),
                        flux=spec_subtracted.flux,
                        uncertainty=spec_subtracted.uncertainty)

                    try:
                        if add_flux:
                            raw_result = analysis.line_flux(freq_spec) * flux_unit
                        else:
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
                    if flux_unit.is_equivalent(u.Jy/solid_angle_in_flux_unit):
                        final_unit = u.Unit(f'W/(m2 {solid_angle_string})')
                    else:
                        final_unit = u.Unit('W/m2')

                    temp_result = raw_result.to(final_unit)
                    if getattr(raw_result, 'uncertainty', None) is not None:
                        temp_result.uncertainty = raw_result.uncertainty.to(final_unit)

                # If the flux unit is instead equivalent to power density
                # (Jy, but defined in wavelength), enforce integration in wavelength space
                elif (flux_unit.is_equivalent(u.Unit('W/(m2 m)')) or
                        flux_unit.is_equivalent(u.Unit(f'W/(m2 m {solid_angle_string})'))):
                    # Perform integration in wavelength space using MKS unit (meters)
                    wave_spec = Spectrum1D(
                        spectral_axis=spec_subtracted.spectral_axis.to(u.m,
                                                                       equivalencies=u.spectral()),
                        flux=spec_subtracted.flux,
                        uncertainty=spec_subtracted.uncertainty)
                    try:
                        if add_flux:
                            raw_result = analysis.line_flux(wave_spec) * flux_unit
                        else:
                            raw_result = raw_result = analysis.line_flux(wave_spec)
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
                    if flux_unit.is_equivalent(u.W / (u.m * u.m * u.m * solid_angle_in_flux_unit)):
                        final_unit = u.Unit(f'W/(m2 {solid_angle_string})')
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
