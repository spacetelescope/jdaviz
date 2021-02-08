import numpy as np
from glue.core.message import (SubsetCreateMessage,
                               SubsetDeleteMessage,
                               SubsetUpdateMessage)
from traitlets import Bool, List, Unicode
from specutils import analysis, SpectralRegion

from jdaviz.core.events import AddDataMessage, RemoveDataMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template

__all__ = ['LineAnalysis']

FUNCTIONS = {"Line Flux": analysis.line_flux,
             "Equivalent Width": analysis.equivalent_width,
             "Gaussian Sigma Width": analysis.gaussian_sigma_width,
             "Gaussian FWHM": analysis.gaussian_fwhm,
             "Centroid": analysis.centroid}


@tray_registry('specviz-line-analysis', label="Line Analysis")
class LineAnalysis(TemplateMixin):
    dialog = Bool(False).tag(sync=True)
    template = load_template("line_analysis.vue", __file__).tag(sync=True)
    dc_items = List([]).tag(sync=True)
    temp_function = Unicode().tag(sync=True)
    available_functions = List(list(FUNCTIONS.keys())).tag(sync=True)
    result_available = Bool(False).tag(sync=True)
    results = List().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._viewer_spectra = None
        self._spectrum1d = None
        self._units = {}
        self.result_available = False

        self.hub.subscribe(self, AddDataMessage,
                           handler=self._on_viewer_data_changed)

        self.hub.subscribe(self, RemoveDataMessage,
                           handler=self._on_viewer_data_changed)

        self.hub.subscribe(self, SubsetCreateMessage,
                           handler=lambda x: self._on_viewer_data_changed())

        self.hub.subscribe(self, SubsetDeleteMessage,
                           handler=lambda x: self._on_viewer_data_changed())

        self.hub.subscribe(self, SubsetUpdateMessage,
                           handler=lambda x: self._on_viewer_data_changed())

    def _on_viewer_data_changed(self, msg=None):
        """
        Callback method for when data is added or removed from a viewer, or
        when a subset is created, deleted, or updated. This method receieves
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
        self._viewer_id = self.app._viewer_item_by_reference(
            'spectrum-viewer').get('id')

        # Subsets are global and are not linked to specific viewer instances,
        # so it's not required that we match any specific ids for that case.
        # However, if the msg is not none, check to make sure that it's the
        # viewer we care about.
        if msg is not None and msg.viewer_id != self._viewer_id:
            return

        viewer = self.app.get_viewer('spectrum-viewer')

        self.dc_items = [layer_state.layer.label
                         for layer_state in viewer.state.layers]

    def vue_data_selected(self, event):
        """
        Callback method for when the user has selected data from the drop down
        in the front-end. It is here that we actually parse and create a new
        data object from the selected data. From this data object, unit
        information is scraped, and the selected spectrum is stored for later
        use in fitting.

        Parameters
        ----------
        event : str
            IPyWidget callback event object. In this case, represents the data
            label of the data collection object selected by the user.
        """
        selected_spec = self.app.get_data_from_viewer("spectrum-viewer",
                                                      data_label=event)

        if self._units == {}:
            self._units["x"] = str(
                selected_spec.spectral_axis.unit)
            self._units["y"] = str(
                selected_spec.flux.unit)

        for label in self.dc_items:
            if label in self.data_collection:
                self._label_to_link = label
                break

        self._spectrum1d = selected_spec

        self._run_functions()

    def _run_functions(self, *args, **kwargs):
        """
        Run fitting on the initialized models, fixing any parameters marked
        as such by the user, then update the displauyed parameters with fit
        values
        """
        temp_results = []
        for function in FUNCTIONS:
            # Centroid function requires a region argument, create one to pass
            if function == "Centroid":
                spectral_axis = self._spectrum1d.spectral_axis
                if self._spectrum1d.mask is None:
                    spec_region = SpectralRegion(spectral_axis[0], spectral_axis[-1])
                else:
                    spec_region = self._spectrum1d.spectral_axis[np.where(self._spectrum1d.mask is
                                                                          False)]
                    spec_region = SpectralRegion(spec_region[0], spec_region[-1])
                temp_result = FUNCTIONS[function](self._spectrum1d, spec_region)
            else:
                temp_result = FUNCTIONS[function](self._spectrum1d)

            temp_results.append({'function': function, 'result': str(temp_result)})
            self.result_available = True

            self.results = []
            self.results = temp_results
