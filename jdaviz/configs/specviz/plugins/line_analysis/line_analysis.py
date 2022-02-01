import numpy as np
from glue.core.message import (SubsetDeleteMessage,
                               SubsetUpdateMessage)
from traitlets import Bool, List, Unicode, observe
from specutils import analysis
from specutils.manipulation import extract_region

from jdaviz.core.custom_traitlets import IntHandleEmpty
from jdaviz.core.events import AddDataMessage, RemoveDataMessage
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
    width_points = IntHandleEmpty(5).tag(sync=True)
    results_computing = Bool(False).tag(sync=True)
    results = List().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._viewer_spectra = None
        self._spectrum1d = None
        self._viewer_id = self.app._viewer_item_by_reference('spectrum-viewer').get('id')
        self._units = {}
        self.update_results(None)

        self.hub.subscribe(self, AddDataMessage,
                           handler=self._on_viewer_data_changed)

        self.hub.subscribe(self, RemoveDataMessage,
                           handler=self._on_viewer_data_changed)

        self.hub.subscribe(self, SubsetDeleteMessage,
                           handler=self._on_viewer_data_changed)

        self.hub.subscribe(self, SubsetUpdateMessage,
                           handler=self._on_viewer_data_changed)

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

    def update_results(self, results=None):
        if results is None:
            self.results = [{'function': function, 'result': ''} for function in FUNCTIONS]
        else:
            self.results = results
        self.results_computing = False

    @observe("selected_subset", "selected_spectrum", "selected_continuum", "width_points")
    def _calculate_statistics(self, *args, **kwargs):
        """
        Run the line analysis functions on the selected data/subset and
        display the results.
        """
        # show spinner, disable, whatever
        self.results_computing = True

        if self.selected_spectrum == "" or self.width_points == "":
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
            inds_bounds = [0, len(spectral_axis)]
            spectrum = self._spectrum1d
        else:

            sr = self.app.get_subsets_from_viewer("spectrum-viewer",
                                                  subset_type="spectral").get(self.selected_subset) # noqa
            spectrum = extract_region(self._spectrum1d, sr, return_single_spectrum=True)

            inds_within_region, = np.where((sr.lower <= spectral_axis) & (spectral_axis <= sr.upper)) # noqa
            inds_bounds = inds_within_region[0], inds_within_region[-1]

        # compute continuum
        if self.selected_continuum == "Surrounding":
            if self.width_points > 50 or self.width_points <= 0:
                # if changing this max-value, also change the value in the
                # rules in line_analysis.vue.  Could make the rule to be
                # dynamic based on the length of the spectrum, but that is
                # likely overkill
                self.update_results(None)
                return

            if inds_bounds[0] < self.width_points:
                # then we need to extend into the line region itself
                left = np.arange(0, self.width_points)
            else:
                left = np.arange(inds_bounds[0]-self.width_points, inds_bounds[0])

            if inds_bounds[1] > len(spectral_axis)-self.width_points:
                # then we need to extend into the line region itself
                right = np.arange(len(spectral_axis)-self.width_points, len(spectral_axis))
            else:
                right = np.arange(inds_bounds[1]+1, inds_bounds[1]+1+self.width_points)

            continuum_mask = np.concatenate((left, right))
        else:
            continuum_mask = self.app.get_data_from_viewer("spectrum-viewer",
                                                           data_label=self.selected_continuum).mask # noqa

        continuum_x = spectral_axis[continuum_mask].value
        continuum_y = self._spectrum1d.flux[continuum_mask].value
        # DEV NOTE: could replace this with internal calls to the model fitting infrastructure
        # to enable other model-types and to give visual feedback (by labeling the model
        # as line_analysis:continuum, for example)
        slope, intercept = np.polyfit(continuum_x, continuum_y, deg=1)
        continuum = slope * spectrum.spectral_axis.value + intercept

        temp_results = []
        for function in FUNCTIONS:
            # TODO: update specutils to allow ALL analysis to take regions and continuum so we
            # don't need these if statements
            if function == "Equivalent Width":
                temp_result = FUNCTIONS[function](spectrum/continuum)
            elif function == "Centroid":
                # TODO: update specutils to be consistent with region vs regions and default to
                # regions=None so this elif can be removed
                temp_result = FUNCTIONS[function](spectrum-continuum, region=None)
            else:
                temp_result = FUNCTIONS[function](spectrum-continuum)

            temp_results.append({'function': function, 'result': str(temp_result)})

        self.update_results(temp_results)
