import numpy as np
import os
from glue.core.message import (SubsetDeleteMessage,
                               SubsetUpdateMessage)
from glue_jupyter.common.toolbar_vuetify import read_icon
from traitlets import Bool, List, Float, Unicode, observe
from astropy import units as u
from specutils import analysis
from specutils.manipulation import extract_region

from jdaviz.core.custom_traitlets import FloatHandleEmpty
from jdaviz.core.events import (SpectralMarksChangedMessage,
                                LineIdentifyMessage,
                                RedshiftMessage)
from jdaviz.core.marks import (LineAnalysisContinuum,
                               LineAnalysisContinuumCenter,
                               LineAnalysisContinuumLeft,
                               LineAnalysisContinuumRight,
                               Shadow)
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin,
                                        DatasetSelectMixin,
                                        SpectralSubsetSelectMixin,
                                        SubsetSelect)
from jdaviz.core.tools import ICON_DIR

__all__ = ['LineAnalysis']

FUNCTIONS = {"Line Flux": analysis.line_flux,
             "Equivalent Width": analysis.equivalent_width,
             "Gaussian Sigma Width": analysis.gaussian_sigma_width,
             "Gaussian FWHM": analysis.gaussian_fwhm,
             "Centroid": analysis.centroid}


@tray_registry('specviz-line-analysis', label="Line Analysis")
class LineAnalysis(PluginTemplateMixin, DatasetSelectMixin, SpectralSubsetSelectMixin):
    dialog = Bool(False).tag(sync=True)
    template_file = __file__, "line_analysis.vue"

    continuum_subset_items = List().tag(sync=True)
    continuum_subset_selected = Unicode().tag(sync=True)

    width = FloatHandleEmpty(3).tag(sync=True)
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
        super().__init__(*args, **kwargs)

        self.update_results(None)

        self.continuum = SubsetSelect(self,
                                      'continuum_subset_items',
                                      'continuum_subset_selected',
                                      default_text='Surrounding',
                                      allowed_type='spectral')

        # when accessing the selected data, access the spectrum-viewer version
        self.dataset._viewers = ['spectrum-viewer']
        # require entries to be in spectrum-viewer (not other cubeviz images, etc)
        self.dataset.add_filter('layer_in_spectrum_viewer')

        self.hub.subscribe(self, SubsetDeleteMessage,
                           handler=self._on_viewer_subsets_changed)
        self.hub.subscribe(self, SubsetUpdateMessage,
                           handler=self._on_viewer_subsets_changed)
        self.hub.subscribe(self, SpectralMarksChangedMessage,
                           handler=self._on_plotted_lines_changed)
        self.hub.subscribe(self, LineIdentifyMessage,
                           handler=self._on_identified_line_changed)

    def _on_viewer_subsets_changed(self, msg):
        """
        Update the statistics if any of the referenced regions have changed

        Parameters
        ----------
        msg : `glue.core.Message`
            The glue message passed to this callback method.
        """
        if (msg.subset.label in [self.spectral_subset_selected, self.continuum_subset_selected]
                and self.plugin_opened):
            self._calculate_statistics()

    @observe('plugin_opened')
    def _on_plugin_opened_changed(self, *args):
        # toggle continuum lines in spectrum viewer based on whether this plugin
        # is currently open in the tray
        for pos, mark in self.marks.items():
            mark.visible = self.plugin_opened
        if self.plugin_opened:
            self._calculate_statistics()

    @property
    def marks(self):
        marks = {}
        viewer = self.app.get_viewer('spectrum-viewer')
        for mark in viewer.figure.marks:
            if isinstance(mark, LineAnalysisContinuum):
                # NOTE: we don't use isinstance anymore because of nested inheritance
                if mark.__class__.__name__ == 'LineAnalysisContinuumLeft':
                    marks['left'] = mark
                elif mark.__class__.__name__ == 'LineAnalysisContinuumCenter':
                    marks['center'] = mark
                elif mark.__class__.__name__ == 'LineAnalysisContinuumRight':
                    marks['right'] = mark

        if not len(marks):
            if not viewer.state.reference_data:
                # we don't have data yet for scales, defer initializing
                return {}
            # then haven't been initialized yet, so initialize with empty
            # marks that will be populated once the first analysis is done.
            marks = {'left': LineAnalysisContinuumLeft(viewer, visible=self.plugin_opened),
                     'center': LineAnalysisContinuumCenter(viewer, visible=self.plugin_opened),
                     'right': LineAnalysisContinuumRight(viewer, visible=self.plugin_opened)}
            shadows = [Shadow(mark, shadow_width=2) for mark in marks.values()]
            # NOTE: += won't trigger the figure to notice new marks
            viewer.figure.marks = viewer.figure.marks + shadows + list(marks.values())

        return marks

    def update_results(self, results=None, mark_x={}, mark_y={}):
        for pos, mark in self.marks.items():
            mark.update_xy(mark_x.get(pos, []), mark_y.get(pos, []))

        if results is None:
            self.results = [{'function': function, 'result': ''} for function in FUNCTIONS]
        else:
            self.results = results

        self.results_computing = False

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

    @observe("spectral_subset_selected", "dataset_selected", "continuum_subset_selected", "width")
    def _calculate_statistics(self, *args, **kwargs):
        """
        Run the line analysis functions on the selected data/subset and
        display the results.
        """
        if not hasattr(self, 'dataset'):
            # during initial init, this can trigger before the component is initialized
            return
        # show spinner with overlay
        self.results_computing = True

        full_spectrum = self.dataset.selected_obj
        if full_spectrum is None or self.width == "" or not self.plugin_opened:
            # this can happen DURING a unit conversion change
            self.update_results(None)
            return

        spectral_axis = full_spectrum.spectral_axis

        if self.continuum_subset_selected == self.spectral_subset_selected:
            # already raised a validation error in the UI
            self.update_results(None)
            return

        if self.spectral_subset_selected != "Surrounding":
            sr = self.app.get_subsets_from_viewer("spectrum-viewer",
                                                  subset_type="spectral").get(self.spectral_subset_selected) # noqa
        else:
            sr = None

        if self.spectral_subset_selected == "Entire Spectrum":
            spectrum = full_spectrum
        else:
            spectrum = extract_region(full_spectrum, sr, return_single_spectrum=True)

        # compute continuum
        if self.continuum_subset_selected == "Surrounding" and self.spectral_subset_selected == "Entire Spectrum": # noqa
            # we know we'll just use the endpoints, so let's be efficient and not even
            # try extracting from the region
            continuum_mask = np.array([0, len(spectral_axis)-1])
            mark_x = {'left': np.array([]),
                      'center': np.array([min(spectral_axis.value), max(spectral_axis.value)]),
                      'right': np.array([])}

        elif self.continuum_subset_selected == "Surrounding":
            # self.spectral_subset_selected != "Entire Spectrum"
            if self.width > 10 or self.width < 1:
                # DEV NOTE: if changing the limits, make sure to also update the form validation
                # rules in line_analysis.vue
                self.update_results(None)
                return

            spectral_region_width = sr.upper - sr.lower
            # convert width from total relative width, to width per "side"
            width = (self.width - 1) / 2
            left, = np.where((spectral_axis < sr.lower) &
                             (spectral_axis > sr.lower - spectral_region_width*width))

            if not len(left):
                # then no points matching the width are available outside the line region,
                # so we'll default to the left-most point of the line region.
                left, = np.where(spectral_axis == min(spectrum.spectral_axis))

            right, = np.where((spectral_axis > sr.upper) &
                              (spectral_axis < sr.upper + spectral_region_width*width))

            if not len(right):
                # then no points matching the width are available outside the line region,
                # so we'll default to the right-most point of the line region.
                right, = np.where(spectral_axis == max(spectrum.spectral_axis))

            continuum_mask = np.concatenate((left, right))
            mark_x = {'left': np.array([min(spectral_axis.value[continuum_mask]), sr.lower.value]),
                      'center': np.array([sr.lower.value, sr.upper.value]),
                      'right': np.array([sr.upper.value, max(spectral_axis.value[continuum_mask])])}

        else:
            continuum_mask = ~self.app.get_data_from_viewer("spectrum-viewer",
                                                            data_label=self.continuum_subset_selected).mask # noqa
            spectral_axis_nanmasked = spectral_axis.value.copy()
            spectral_axis_nanmasked[~continuum_mask] = np.nan
            if self.spectral_subset_selected == "Entire Spectrum":
                mark_x = {'left': spectral_axis_nanmasked,
                          'center': spectral_axis.value,
                          'right': []}
            else:
                mark_x = {'left': spectral_axis_nanmasked[spectral_axis.value < sr.lower.value],
                          'right': spectral_axis_nanmasked[spectral_axis.value > sr.upper.value]}
                # center should extend (at least) across the line region between the full
                # range defined by the continuum subset(s)
                left_min = np.nanmin([np.nanmin(mark_x['left']), sr.lower.value])
                right_max = np.nanmax([np.nanmax(mark_x['right']), sr.upper.value])
                mark_x['center'] = np.array([left_min, right_max])

        continuum_x = spectral_axis[continuum_mask].value
        min_x = min(spectral_axis.value)
        continuum_y = full_spectrum.flux[continuum_mask].value
        # DEV NOTE: could replace this with internal calls to the model fitting infrastructure
        # to enable other model-types and to give visual feedback (by labeling the model
        # as line_analysis:continuum, for example)
        slope, intercept = np.polyfit(continuum_x-min_x, continuum_y, deg=1)
        continuum = slope * (spectrum.spectral_axis.value-min_x) + intercept
        mark_y = {k: slope * (v-min_x) + intercept for k, v in mark_x.items()}

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
        spec_subtracted = spectrum - continuum
        for function in FUNCTIONS:
            # TODO: update specutils to allow ALL analysis to take regions and continuum so we
            # don't need these if statements
            if function == "Equivalent Width":
                if np.any(continuum <= 0):
                    temp_results.append({'function': function,
                                         'result': '',
                                         'error_msg': 'N/A (continuum <= 0)',
                                         'uncertainty': '',
                                         'unit': ''})
                    continue
                else:
                    spec_normalized = spectrum / continuum
                    temp_result = FUNCTIONS[function](spec_normalized)
            elif function == "Centroid":
                # TODO: update specutils to be consistent with region vs regions and default to
                # regions=None so this elif can be removed
                temp_result = FUNCTIONS[function](spec_subtracted, region=None)
                self.results_centroid = temp_result.to_value(u.AA, equivalencies=u.spectral())
            else:
                temp_result = FUNCTIONS[function](spec_subtracted)

            temp_results.append({'function': function,
                                 'result': str(temp_result.value),
                                 'uncertainty': _uncertainty(temp_result),
                                 'unit': str(temp_result.unit)})

        if not self.selected_line and self.identified_line:
            # default to the identified line
            self.selected_line = self.identified_line

        self.update_results(temp_results, mark_x, mark_y)

    def _compute_redshift_for_selected_line(self):
        index = self.line_items.index(self.selected_line)
        line_mark = self.line_marks[index]
        rest_value = (line_mark.rest_value * line_mark._x_unit).to_value(u.AA,
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
