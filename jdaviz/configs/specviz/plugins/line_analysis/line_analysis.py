import numpy as np
from glue.core.message import (SubsetDeleteMessage,
                               SubsetUpdateMessage)
from traitlets import Bool, List, Unicode, observe
from specutils import analysis
from specutils.manipulation import extract_region

from jdaviz.core.custom_traitlets import FloatHandleEmpty
from jdaviz.core.events import AddDataMessage, RemoveDataMessage
from jdaviz.core.marks import (LineAnalysisContinuum,
                               LineAnalysisContinuumCenter,
                               LineAnalysisContinuumLeft,
                               LineAnalysisContinuumRight)
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin

__all__ = ['LineAnalysis']

FUNCTIONS = {"Line Flux": analysis.line_flux,
             "Equivalent Width": analysis.equivalent_width,
             "Gaussian Sigma Width": analysis.gaussian_sigma_width,
             "Gaussian FWHM": analysis.gaussian_fwhm,
             "Centroid": analysis.centroid}


@tray_registry('specviz-line-analysis', label="Line Analysis")
class LineAnalysis(TemplateMixin):
    dialog = Bool(False).tag(sync=True)
    template_file = __file__, "line_analysis.vue"
    dc_items = List([]).tag(sync=True)
    spectral_subset_items = List(["Entire Spectrum"]).tag(sync=True)
    selected_spectrum = Unicode("").tag(sync=True)
    selected_subset = Unicode("Entire Spectrum").tag(sync=True)
    continuum_subset_items = List(["Surrounding"]).tag(sync=True)
    selected_continuum = Unicode("Surrounding").tag(sync=True)
    width = FloatHandleEmpty(3).tag(sync=True)
    results_computing = Bool(False).tag(sync=True)
    results = List().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._viewer_spectra = None
        self._spectrum1d = None
        self._viewer_id = self.app._viewer_item_by_reference('spectrum-viewer').get('id')
        self._units = {}
        self._is_opened = False
        self.update_results(None)

        self.hub.subscribe(self, AddDataMessage,
                           handler=self._on_viewer_data_changed)

        self.hub.subscribe(self, RemoveDataMessage,
                           handler=self._on_viewer_data_changed)

        self.hub.subscribe(self, SubsetDeleteMessage,
                           handler=self._on_viewer_data_changed)

        self.hub.subscribe(self, SubsetUpdateMessage,
                           handler=self._on_viewer_data_changed)

        self.app.state.add_callback('tray_items_open', self._on_plugin_opened_changed)
        self.app.state.add_callback('drawer', self._on_plugin_opened_changed)

    def _on_viewer_data_changed(self, msg=None):
        """
        Callback method for when data is added or removed from a viewer, or
        when a subset is created, deleted, or updated. This method receives
        a glue message containing viewer information in the case of the former
        set of events, and updates the available data list displayed to the
        user.

        Notes
        -----
        We do not attempt to parse any data at this point, at it can cause
        visible lag in the application.

        Parameters
        ----------
        msg : `glue.core.Message`
            The glue message passed to this callback method.
        """
        viewer = self.app.get_viewer('spectrum-viewer')

        try:
            self._spectral_subsets = self.app.get_subsets_from_viewer("spectrum-viewer",
                                                                      subset_type="spectral")
        except ValueError:
            pass

        self.spectral_subset_items = ["Entire Spectrum"] + sorted(self._spectral_subsets.keys())
        self.continuum_subset_items = ["Surrounding"] + sorted(self._spectral_subsets.keys())

        self.dc_items = [layer_state.layer.label for layer_state in viewer.state.layers
                         if layer_state.layer.label not in self.spectral_subset_items]

        if self.selected_spectrum == "":
            # default to first entry in list instead of leaving empty
            self.selected_spectrum = self.dc_items[0]

        if len(self.dc_items) == 0:
            self.selected_spectrum = ""
            self.selected_subset = "Entire Spectrum"
            self.selected_continuum = "Surrounding"
            self.update_results(None)
        elif isinstance(msg, SubsetUpdateMessage):
            if msg.subset.label in [self.selected_subset, self.selected_continuum]:
                self._calculate_statistics()

    def _on_plugin_opened_changed(self, new_value):
        # toggle continuum lines in spectrum viewer based on whether this plugin
        # is currently open in the tray
        app_state = self.app.state
        tray_names_open = [app_state.tray_items[i]['name'] for i in app_state.tray_items_open]
        self._is_opened = app_state.drawer and 'specviz-line-analysis' in tray_names_open
        for pos, mark in self.marks.items():
            mark.visible = self._is_opened

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
            marks = {'left': LineAnalysisContinuumLeft(viewer, visible=self._is_opened),
                     'center': LineAnalysisContinuumCenter(viewer, visible=self._is_opened),
                     'right': LineAnalysisContinuumRight(viewer, visible=self._is_opened)}
            # NOTE: += won't trigger the figure to notice new marks
            viewer.figure.marks = viewer.figure.marks + list(marks.values())

        return marks

    def update_results(self, results=None, mark_x={}, mark_y={}):
        for pos, mark in self.marks.items():
            mark.update_xy(mark_x.get(pos, []), mark_y.get(pos, []))

        if results is None:
            self.results = [{'function': function, 'result': ''} for function in FUNCTIONS]
        else:
            self.results = results

        self.results_computing = False

    @observe("selected_subset", "selected_spectrum", "selected_continuum", "width")
    def _calculate_statistics(self, *args, **kwargs):
        """
        Run the line analysis functions on the selected data/subset and
        display the results.
        """
        # show spinner, disable, whatever
        self.results_computing = True

        if self.selected_spectrum == "" or self.width == "":
            self.update_results(None)
            return

        self._spectrum1d = self.app.get_data_from_viewer("spectrum-viewer",
                                                         data_label=self.selected_spectrum)
        spectral_axis = self._spectrum1d.spectral_axis

        if self.selected_continuum == self.selected_subset:
            # already raised a validation error in the UI
            self.update_results(None)
            return
        elif self.selected_subset == "Entire Spectrum":
            spectrum = self._spectrum1d
        else:
            sr = self.app.get_subsets_from_viewer("spectrum-viewer",
                                                  subset_type="spectral").get(self.selected_subset) # noqa
            spectrum = extract_region(self._spectrum1d, sr, return_single_spectrum=True)

        # compute continuum
        if self.selected_continuum == "Surrounding" and self.selected_subset == "Entire Spectrum":
            # we know we'll just use the endpoints, so let's be efficient and not even
            # try extracting from the region
            continuum_mask = np.array([0, len(spectral_axis)-1])
            mark_x = {'left': np.array([]),
                      'center': np.array([spectral_axis.value[0], spectral_axis.value[-1]]),
                      'right': np.array([])}

        elif self.selected_continuum == "Surrounding":
            if self.width > 10 or self.width < 1:
                # DEV NOTE: if changing the limits, make sure to also update the form validation
                # rules in line_analysis.vue
                self.update_results(None)
                return

            spectral_region_width = sr.upper - sr.lower
            # convert width from total relative width, to width per "side"
            width = (self.width - 1) / 2
            left, = np.where((spectral_axis < sr.lower) &
                             (spectral_axis >= sr.lower - spectral_region_width*width))

            if not len(left):
                # then no points matching the width are available outside the line region,
                # so we'll default to the left-most point of the line region.
                left, = np.where(spectral_axis == spectrum.spectral_axis[:1])

            right, = np.where((spectral_axis > sr.upper) &
                              (spectral_axis <= sr.upper + spectral_region_width*width))

            if not len(right):
                # then no points matching the width are available outside the line region,
                # so we'll default to the right-most point of the line region.
                right, = np.where(spectral_axis == spectrum.spectral_axis[-1:])

            continuum_mask = np.concatenate((left, right))
            mark_x = {'left': np.array([spectral_axis.value[continuum_mask[0]], sr.lower.value]),
                      'center': np.array([sr.lower.value, sr.upper.value]),
                      'right': np.array([sr.upper.value, spectral_axis.value[continuum_mask[-1]]])}

        else:
            continuum_mask = ~self.app.get_data_from_viewer("spectrum-viewer",
                                                            data_label=self.selected_continuum).mask # noqa
            spectral_axis_nanmasked = spectral_axis.value.copy()
            spectral_axis_nanmasked[~continuum_mask] = np.nan
            mark_x = {'left': spectral_axis_nanmasked[spectral_axis.value < sr.lower.value],
                      'center': np.array([sr.lower.value, sr.upper.value]),
                      'right': spectral_axis_nanmasked[spectral_axis.value > sr.upper.value]}

        continuum_x = spectral_axis[continuum_mask].value
        min_x = min(spectral_axis.value)
        continuum_y = self._spectrum1d.flux[continuum_mask].value
        # DEV NOTE: could replace this with internal calls to the model fitting infrastructure
        # to enable other model-types and to give visual feedback (by labeling the model
        # as line_analysis:continuum, for example)
        slope, intercept = np.polyfit(continuum_x-min_x, continuum_y, deg=1)
        continuum = slope * (spectrum.spectral_axis.value-min_x) + intercept
        mark_y = {k: slope * (v-min_x) + intercept for k, v in mark_x.items()}

        temp_results = []
        for function in FUNCTIONS:
            # TODO: update specutils to allow ALL analysis to take regions and continuum so we
            # don't need these if statements
            if function == "Equivalent Width":
                if np.any(continuum <= 0):
                    temp_result = 'N/A (continuum <= 0)'
                else:
                    temp_result = FUNCTIONS[function](spectrum/continuum)
            elif function == "Centroid":
                # TODO: update specutils to be consistent with region vs regions and default to
                # regions=None so this elif can be removed
                temp_result = FUNCTIONS[function](spectrum-continuum, region=None)
            else:
                temp_result = FUNCTIONS[function](spectrum-continuum)

            temp_results.append({'function': function, 'result': str(temp_result)})

        self.update_results(temp_results, mark_x, mark_y)
