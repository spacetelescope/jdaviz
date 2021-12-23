import numpy as np
from glue.core.message import (SubsetDeleteMessage,
                               SubsetUpdateMessage)
from traitlets import Bool, List, Unicode, observe
from specutils import analysis, SpectralRegion

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
    result_available = Bool(False).tag(sync=True)
    results = List().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._viewer_spectra = None
        self._spectrum1d = None
        self._viewer_id = self.app._viewer_item_by_reference('spectrum-viewer').get('id')
        self._units = {}
        self.result_available = False

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

        self.dc_items = [layer_state.layer.label for layer_state in viewer.state.layers
                         if layer_state.layer.label not in self.spectral_subset_items]

        if len(self.dc_items) == 0:
            self.selected_spectrum = ""
            self.selected_subset = "Entire Spectrum"
            self.result_available = False

    @observe("selected_subset", "selected_spectrum")
    def _calculate_statistics(self, *args, **kwargs):
        """
        Run the line analysis functions on the selected data/subset and
        display the results.
        """
        if self.selected_spectrum == "":
            self.result_available = False
            return

        self._spectrum1d = self.app.get_data_from_viewer("spectrum-viewer",
                                                         data_label=self.selected_spectrum)

        if self.selected_subset != "Entire Spectrum":
            mask = self.app.get_data_from_viewer("spectrum-viewer",
                                                 data_label=self.selected_subset).mask
            self._spectrum1d.mask = mask

        temp_results = []
        for function in FUNCTIONS:
            # Centroid function requires a region argument, create one to pass
            if function == "Centroid":
                spectral_axis = self._spectrum1d.spectral_axis
                if self._spectrum1d.mask is None:
                    spec_region = SpectralRegion(spectral_axis[0], spectral_axis[-1])
                else:
                    spec_region = self._spectrum1d.spectral_axis[np.where(
                                                                 self._spectrum1d.mask == 0)]
                    spec_region = SpectralRegion(spec_region[0], spec_region[-1])
                temp_result = FUNCTIONS[function](self._spectrum1d, spec_region)
            else:
                temp_result = FUNCTIONS[function](self._spectrum1d)

            temp_results.append({'function': function, 'result': str(temp_result)})

        self.results = temp_results
        self.result_available = True
