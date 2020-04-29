import pickle

from glue.core.message import (DataCollectionAddMessage,
                               DataCollectionDeleteMessage)
from traitlets import Bool, List, Dict, Unicode
import astropy.units as u
import astropy.modeling.models as models
from specutils.spectra import Spectrum1D


from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template

from .fitting_backend import fit_model_to_spectrum

__all__ = ['ModelFitting']

def get_params(model_dict):
    return {x["name"]: u.Quantity(x["value"], x["unit"]) for x in model_dict["parameters"]}

def get_fixed(model_dict):
    return {x["name"]: x["fixed"] for x in model_dict["parameters"]}

def initialize_gaussian1d(model_dict):
    params = get_params(model_dict)
    fixed = get_fixed(model_dict)
    return models.Gaussian1D(amplitude=params["amplitude"],
                             mean=params["mean"],
                             stddev=params["stddev"],
                             name=model_dict["id"],
                             fixed = fixed)

def initialize_const1d(model_dict):
    params = get_params(model_dict)
    fixed = get_fixed(model_dict)
    return models.Const1D(amplitude=params["amplitude"],
                          name=model_dict["id"],
                          fixed = fixed)

model_initializers = {"Gaussian1D": initialize_gaussian1d,
                      "Const1D": initialize_const1d}

model_parameters = {"Gaussian1D": ["amplitude", "stddev", "mean"],
                    "Const1D": ["amplitude"]}

@tray_registry('g-model-fitting')
class ModelFitting(TemplateMixin):
    dialog = Bool(False).tag(sync=True)
    template = load_template("model_fitting.vue", __file__).tag(sync=True)
    dc_items = List([]).tag(sync=True)

    temp_name = Unicode().tag(sync=True)
    temp_model = Unicode().tag(sync=True)
    model_equation = Unicode().tag(sync=True)
    param_units = Dict({}).tag(sync=True)
    eq_error = Bool(False).tag(sync=True)
    component_models = List([]).tag(sync=True)

    # Hard coding this for now, but will want to pull from a config file
    available_models = List(["Gaussian1D", "Const1D"]).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hub.subscribe(self, DataCollectionAddMessage,
                           handler=self._on_data_updated)
        self.hub.subscribe(self, DataCollectionDeleteMessage,
                          handler=self._on_data_updated)

        self._selected_data = None
        self._spectrum1d = None
        self._fitted_model = None
        self._fitted_spectrum = None
        # Hard coding this for initial testing, want to populate based on
        # selected data
        self._param_units = {"amplitude": "1E-17 erg/s/cm^2/Angstrom/spaxel",
                             "stddev": "m",
                             "mean": "m"}
        self.component_models = []

    def _on_data_updated(self, msg):
       self.dc_items = [x.label for x in self.data_collection]

    def vue_data_selected(self, event):
        self._selected_data = next((x for x in self.data_collection
                                    if x.label == event))
        self._spectrum1d = self._selected_data.get_object(cls=Spectrum1D)

    def vue_model_selected(self, event):
        # Add the model selected to the list of models
        self.temp_model = event

    def vue_add_model(self, event):
        # Add the selected model and input string ID to the list of models
        new_model = {"id": self.temp_name, "model_type": self.temp_model,
                     "parameters": []}
        for param in model_parameters[new_model["model_type"]]:
            new_model["parameters"].append({"name": param, "value": None,
                                            "unit": self._param_units[param],
                                            "fixed": False})
        self.component_models = self.component_models + [new_model]

    def vue_remove_model(self, event):
        self.component_models = [x for x in self.component_models if x["id"] != event]

    def vue_save_model(self, event):
        with open('fitted_model.pkl', 'wb') as f:
            pickle.dump(self._fitted_model, f)

    def vue_equation_changed(self, event):
        # Length is a dummy check to test the infrastructure
        if len(self.model_equation) > 6:
            self.eq_error = True

    def vue_model_fitting(self, *args, **kwargs):
        # This will be where the model fitting code is run
        initialized_models = [model_initializers[x["model_type"]](x) for x in self.component_models]
        fitted_model, fitted_spectrum = fit_model_to_spectrum(self._spectrum1d,
                                                              initialized_models,
                                                              self.model_equation)
        self._fitted_model = fitted_model
        self._fitted_spectrum = fitted_spectrum
        self.data_collection["Model fit"] = self._fitted_spectrum
        self.dialog = False
