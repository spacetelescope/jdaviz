import os

import numpy as np
from astropy.units import UnitConversionError
from glue.core.message import (SubsetDeleteMessage,
                               SubsetUpdateMessage)
from glue_jupyter.common.toolbar_vuetify import read_icon
from traitlets import Bool, List, Float, Unicode, observe
from astropy import units as u
from astropy.modeling.models import Gaussian1D, Const1D
from specutils import analysis, Spectrum

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
from jdaviz.core.marks import BaseSpectrumVerticalLine, PluginLine
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin,
                                        DatasetSelectMixin,
                                        TableMixin,
                                        SpectralSubsetSelectMixin,
                                        DatasetSpectralSubsetValidMixin,
                                        SpectralContinuumMixin,
                                        CustomToolbarToggleMixin,
                                        AddResultsMixin,
                                        with_spinner)
from jdaviz.core.user_api import PluginUserApi
from jdaviz.core.tools import ICON_DIR
from jdaviz.core.unit_conversion_utils import (is_unit_per_solid_angle,
                                               coerce_unit)


__all__ = ['LineAnalysis']

FUNCTIONS = {"Line Flux": analysis.line_flux,
             "Equivalent Width": analysis.equivalent_width,
             "Gaussian Sigma Width": analysis.gaussian_sigma_width,
             "Gaussian FWHM": analysis.gaussian_fwhm,
             "Centroid": analysis.centroid}


@tray_registry('specviz-line-analysis', label="Line Analysis", category="data:analysis")
class LineAnalysis(PluginTemplateMixin, DatasetSelectMixin, TableMixin,
                   SpectralSubsetSelectMixin, DatasetSpectralSubsetValidMixin,
                   SpectralContinuumMixin, CustomToolbarToggleMixin, AddResultsMixin):
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
    * ``add_results`` (:class:`~jdaviz.core.template_mixin.AddResults`)
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
    plot_analysis_marks = Bool(True).tag(sync=True)
    plot_gaussian_spectrum = Bool(True).tag(sync=True)
    plot_centroid_line = Bool(True).tag(sync=True)
    plot_fwhm_line = Bool(True).tag(sync=True)
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

        if self.config == 'deconfigged':
            self.docs_link = f'https://jdaviz.readthedocs.io/en/{self.vdocs}/plugins/line_analysis.html'  # noqa

        self.update_results(None)

        # require entries to be in spectrum-viewer (not other cubeviz images, etc)
        self.dataset.add_filter('layer_in_spectrum_viewer')

        # continuum selection is mandatory for line-analysis
        self._continuum_remove_none_option()

        def custom_toolbar(viewer):
            if isinstance(viewer, Spectrum1DViewer):
                return viewer.toolbar._original_tools_nested[:3] + [['jdaviz:selectline']], 'jdaviz:selectline'  # noqa
            # otherwise defaults
            return None, None

        self.custom_toolbar.callable = custom_toolbar
        self.custom_toolbar.name = "Spectral Line Selection"

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

        self.observe_traitlets_for_relevancy(traitlets_to_observe=['dataset_items'],
                                             irrelevant_msg_callback=self._irrelevant_msg_callback)

    def _irrelevant_msg_callback(self, *args):
        if self._app.config == 'deconfigged':
            if not len(self.dataset_items):
                irrelevant_msg = 'Line Analysis unavailable without data loaded in spectrum viewer'  # noqa
            else:
                irrelevant_msg = ''
        else:
            sv = self.spectrum_viewer
            if sv is None:
                irrelevant_msg = 'Line Analysis unavailable without spectrum viewer'
            elif not len(sv.layers):
                irrelevant_msg = ''
                self.disabled_msg = 'Line Analysis unavailable without data loaded in spectrum viewer'  # noqa
            else:
                irrelevant_msg = ''
                self.disabled_msg = ''

        return irrelevant_msg

    @property
    def user_api(self):
        return PluginUserApi(self, expose=('dataset', 'spectral_subset',
                                           'continuum', 'continuum_width', 'get_results',
                                           'export_table', 'add_results', 'plot_gaussian_spectrum',
                                           'plot_centroid_line', 'plot_fwhm_line'))

    @property
    def line_items(self):
        # Return list of only the table indices ("name_rest" in line table) from line_menu_items
        return [item["value"] for item in self.line_menu_items]

    def _on_viewers_changed(self, msg):
        # when accessing the selected data, access the spectrum-viewer version
        self.dataset._viewers = [v.reference_id for v in self._app._viewer_store.values()
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

        viewer_data = self._app._jdaviz_helper.get_data(data_label=msg.data.label)

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

    def _reset_results_and_marks(self):
        """Reset results, results_available, and clear continuum marks."""
        self.results_available = False
        self.results = [{'function': function, 'result': ''} for function in FUNCTIONS]
        self._update_continuum_marks()

    def _on_viewer_subsets_changed(self, msg):
        """
        Update the statistics if the current selection spectral region has been
        modified or deleted.

        Parameters
        ----------
        msg : `glue.core.Message`
            The glue message passed to this callback method.
        """

        current_selections = [self.spectral_subset_selected,
                              self.continuum_subset_selected]

        # If a currently selected subset is deleted, just clear marks and statistics.
        # The re-calculation of statistics will happen subsequently when the default
        # selection is applied in the drop down and this method is called again
        if isinstance(msg, SubsetDeleteMessage):
            if msg.subset.label in current_selections:
                self._reset_results_and_marks()
                return

        else:
            if msg.subset.label in current_selections:
                self._calculate_statistics(msg)

    def _on_global_display_unit_changed(self, msg):
        update_marks = msg.axis != 'spectral'
        self._calculate_statistics(msg, update_marks=update_marks)

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
            self._reset_results_and_marks()
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

    @observe("dataset_selected", "dataset_items")
    def _set_default_results_label(self, event={}):
        label_comps = []
        if hasattr(self, 'dataset') and (len(self.dataset.labels) > 1):  # noqa
            label_comps += [self.dataset_selected]
        label_comps += ["fit"]
        self.results_label_default = " ".join(label_comps)

    def _get_gaussian_parameters(self):
        params = self.results
        line_flux = float(params[0]['result']) * u.Unit(params[0]['unit'])
        sigma = float(params[2]['result']) * u.Unit(params[2]['unit'])
        fwhm = float(params[3]['result']) * u.Unit(params[3]['unit'])
        centroid = float(params[4]['result']) * u.Unit(params[4]['unit'])

        # have to convert from integrated line flux to peak amplitude
        amplitude_flam = (line_flux / (sigma * np.sqrt(2 * np.pi))).to(u.Unit(params[0]['unit']/u.Unit(params[2]['unit']))) # noqa
        try:
            amplitude_jy = amplitude_flam.to(u.Jy, equivalencies=u.spectral_density(centroid))
        except UnitConversionError:
            amplitude_jy = amplitude_flam
        _, continuum, _ = self._get_continuum(self.dataset,self.spectral_subset)

        parameters = {'centroid': centroid, 'amplitude': amplitude_jy, 'sigma': sigma, 'fwhm': fwhm, 'continuum': continuum}
        return parameters

    def _create_gaussian_spectrum(self, parameters, spectrum_template):
        """Create a 1D Gaussian model using the provided parameters and return it as a Spectrum object."""

        gaussian_model = Gaussian1D(amplitude=parameters['amplitude'].value,
                                    mean=parameters['centroid'].value,
                                    stddev=parameters['sigma'].value)
        continuum_offset = Const1D(amplitude=np.median(parameters['continuum']))

        # oversample the spectrum to get a smooth curve for plotting
        interp_spec_axis = np.linspace(spectrum_template.spectral_axis.value.min(),
                                        spectrum_template.spectral_axis.value.max(),
                                        5*len(spectrum_template.spectral_axis.value))
        flux_values = gaussian_model(interp_spec_axis) + continuum_offset(interp_spec_axis)

        x_display_unit = self.spectrum_viewer.state.x_display_unit
        y_display_unit = self.spectrum_viewer.state.y_display_unit
        try:
            gaussian_spectrum = Spectrum(spectral_axis=interp_spec_axis * u.Unit(x_display_unit),
                                       flux=(flux_values * parameters['amplitude'].unit).to(y_display_unit))
        except UnitConversionError:
            gaussian_spectrum = None

        return gaussian_spectrum

    def _create_centroid_line(self, centroid_value):
        """
        Create a vertical line at the centroid value from line analysis results.
        """
        if self.spectrum_viewer is None:
            return None

        # Convert centroid value to the current display unit of the spectrum viewer
        display_unit = spec_viewer.state.x_display_unit
        centroid_in_display_unit = centroid_value.to(display_unit,
                                                              equivalencies=u.spectral()).value

        # Create a vertical line at the centroid value
        line = BaseSpectrumVerticalLine(viewer=spec_viewer,
                                        x=centroid_in_display_unit,
                                        colors=['#0511F7'],
                                        stroke_width=2,
                                        line_style='dash_dotted')

        return line

    def _create_fwhm_line(self, amplitude_value, centroid_value, fwhm_value, continuum):
        """
        Create a horizontal line at the FWHM value from line analysis results.
        """
        if self.spectrum_viewer is None:
            return None

        # Convert centroid and FWHM values to the current display unit of the spectrum viewer
        x_display_unit = spec_viewer.state.x_display_unit
        centroid_in_display_unit = centroid_value.to(x_display_unit,
                                                     equivalencies=u.spectral()).value
        fwhm_in_display_unit = fwhm_value.to(x_display_unit,
                                             equivalencies=u.spectral()).value

        # Calculate the y-value for the FWHM line based on the amplitude
        y_display_unit = spec_viewer.state.y_display_unit
        continuum_offset = np.median(continuum)
        y_value = amplitude_value.to(y_display_unit).value / 2 + continuum_offset.value  # FWHM is half of the amplitude

        # Create a horizontal line at the FWHM value
        line = PluginLine(viewer=spec_viewer,
                          x=[centroid_in_display_unit - fwhm_in_display_unit / 2,
                             centroid_in_display_unit + fwhm_in_display_unit / 2],
                          y=[y_value, y_value],
                          colors=['#D41159'],
                          stroke_width=2,
                          line_style='solid')

        return line

    def _clear_analysis_marks(self):
        if self.spectrum_viewer is None:
            return

        for viewer_id, viewer in self._app._viewer_store.items():
            if isinstance(viewer, Spectrum1DViewer):
                spec_viewer = viewer
                break

        marks_to_keep = []
        for mark in self.spectrum_viewer.figure.marks:
            # remove only our marks (centroid and FWHM lines)
            if mark is not getattr(self, '_centroid_line', None) and \
                    mark is not getattr(self, '_fwhm_line', None):
                marks_to_keep.append(mark)

        spec_viewer.figure.marks = marks_to_keep

        # reset
        self._centroid_line = None
        self._fwhm_line = None

    def _plot_analysis_marks(self, parameters):
        """
        Plot the centroid and FWHM lines on the spectrum viewer based on the
        provided parameters from the line analysis results.
        """
        if self.spectrum_viewer is None:
            return

        for viewer_id, viewer in self._app._viewer_store.items():
            if isinstance(viewer, Spectrum1DViewer):
                spec_viewer = viewer
                break

        self._clear_analysis_marks()

        try:
            centroid_value = parameters['centroid'].to(u.Unit(spec_viewer.state.x_display_unit))
            fwhm_value = parameters['fwhm'].to(u.Unit(spec_viewer.state.x_display_unit))
            amplitude_value = parameters['amplitude'].to(u.Unit(spec_viewer.state.y_display_unit))
            continuum = parameters['continuum'] * u.Unit(spec_viewer.state.y_display_unit)

            if self.plot_centroid_line:
                self._centroid_line = self._create_centroid_line(centroid_value)
                if self._centroid_line is not None:
                    spec_viewer.figure.marks += [self._centroid_line]

            if self.plot_fwhm_line:
                self._fwhm_line = self._create_fwhm_line(amplitude_value, centroid_value,
                                                     fwhm_value, continuum)
                if self._fwhm_line is not None:
                    spec_viewer.figure.marks += [self._fwhm_line]

            spec_viewer.figure.send_state('marks')
        except Exception as e:
            self.hub.broadcast(SnackbarMessage(
                f"failed to plot analysis marks: {e}", sender=self,
                color="warning", traceback=e))

    @observe('plot_gaussian_spectrum', 'plot_centroid_line', 'plot_fwhm_line')
    def _on_plot_toggles_changed(self, event):
        """Clear marks when toggle states change."""
        self._clear_analysis_marks()

    @observe('spectral_subset_selected', 'continuum_subset_selected')
    def _on_subset_changed_clear_marks(self, event):
        """Clear marks when subsets change (before recalculation happens)."""
        self._clear_analysis_marks()

    @observe("dataset_selected", "spectral_subset_selected",
             "continuum_subset_selected", "continuum_width")
    @with_spinner('results_computing')
    def _calculate_statistics(self, msg={}, store_results=False,
                              update_marks=True):
        """
        Run the line analysis functions on the selected data/subset and
        display the results.
        """

        if not hasattr(self, 'dataset') or self._app._jdaviz_helper is None:  # noqa
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
                                                                   update_marks=update_marks)
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

                solid_angle_in_flux_unit = is_unit_per_solid_angle(
                    flux_unit, return_unit=True)
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
                    freq_spec = Spectrum(
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
                            color="warning", traceback=e))
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
                    wave_spec = Spectrum(
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
                            color="warning", traceback=e))
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
                temp_result = FUNCTIONS[function](spec_subtracted)

            temp_result = coerce_unit(temp_result)
            temp_results.append({'function': function,
                                 'result': str(temp_result.value),
                                 'uncertainty': _uncertainty(temp_result),
                                 'unit': str(temp_result.unit)})

        if not self.selected_line and self.identified_line:
            # default to the identified line
            self.selected_line = self.identified_line

        self.update_results(temp_results)

        params = self._get_gaussian_parameters()
        gaussian_spectrum = self._create_gaussian_spectrum(params, spectrum)

        load_kwargs = {}
        if self.add_results.viewer.selected not in (None, 'None'):
            load_kwargs['viewer'] = self.add_results.viewer.selected
        else:
            load_kwargs['viewer'] = self.spectrum_viewer.reference_id

        if self.plot_gaussian_spectrum and gaussian_spectrum is not None:
            self._set_default_results_label()
            if self.add_results.viewer.selected not in (None, 'None'):
                load_kwargs['viewer'] = self.add_results.viewer.selected
            else:
                # find first 1D spectrum viewer (necessary to find the
                # auto-extracted 1D spectrum viewer in cubeviz/specviz2d)
                for viewer_id, viewer in self._app._viewer_store.items():
                    if isinstance(viewer, Spectrum1DViewer):
                        load_kwargs['viewer'] = viewer_id
                        break
            self.add_results.add_results_from_plugin(
                gaussian_spectrum, label="Gaussian Fit", format="1D Spectrum", load_kwargs=load_kwargs)

        if self.plot_centroid_line or self.plot_fwhm_line:
            self._plot_analysis_marks(params)

        # run again to reset
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
