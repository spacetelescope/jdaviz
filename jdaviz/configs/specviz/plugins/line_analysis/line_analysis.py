import os
import pickle

import astropy.modeling.models as models
import astropy.units as u
from glue.core.link_helpers import LinkSame
from glue.core.message import (SubsetCreateMessage,
                               SubsetDeleteMessage,
                               SubsetUpdateMessage)
from traitlets import Bool, Int, List, Unicode

from jdaviz.core.events import AddDataMessage, RemoveDataMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template
from .fitting_backend import fit_model_to_spectrum
from .initializers import initialize, model_parameters

__all__ = ['ModelFitting']

FUNCTIONS = {}

MODELS = {
     'Const1D': models.Const1D,
     'Linear1D': models.Linear1D,
     'Polynomial1D': models.Polynomial1D,
     'Gaussian1D': models.Gaussian1D,
     'Voigt1D': models.Voigt1D,
     'Lorentz1D': models.Lorentz1D
     }


@tray_registry('specviz-line-analysis', label="Line Analysis")
class ModelFitting(TemplateMixin):
    dialog = Bool(False).tag(sync=True)
    template = load_template("line_analysis.vue", __file__).tag(sync=True)
    dc_items = List([]).tag(sync=True)
    temp_function = Unicode().tag(sync=True)
    available_functions = List(list(FUNCTIONS.keys())).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._viewer_spectra = None
        self._spectrum1d = None
        self._units = {}

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

    def vue_function_selected(self, event):
        # Add the model selected to the list of models
        self.temp_function = event

    def vue_add_model(self, event):
        """Add the selected model and input string ID to the list of models"""
        new_model = {"id": self.temp_name, "model_type": self.temp_model,
                     "parameters": []}

        # Need to do things differently for polynomials, since the order varies
        if self.temp_model == "Polynomial1D":
            new_model = self._initialize_polynomial(new_model)
        else:
            # Have a separate private dict with the initialized models, since
            # they don't play well with JSON for widget interaction
            initialized_model = initialize(
                MODELS[self.temp_model](name=self.temp_name),
                self._spectrum1d.spectral_axis,
                self._spectrum1d.flux)

            self._initialized_models[self.temp_name] = initialized_model

            for param in model_parameters[new_model["model_type"]]:
                initial_val = getattr(initialized_model, param).value
                new_model["parameters"].append({"name": param,
                                                "value": initial_val,
                                                "unit": self._param_units(param),
                                                "fixed": False})

        new_model["Initialized"] = True
        self.component_models = self.component_models + [new_model]

    def vue_run_function(self, *args, **kwargs):
        """
        Run fitting on the initialized models, fixing any parameters marked
        as such by the user, then update the displauyed parameters with fit
        values
        """
        pass
