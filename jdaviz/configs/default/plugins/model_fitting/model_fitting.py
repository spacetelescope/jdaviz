import re
import numpy as np

import astropy.modeling.models as models
import astropy.units as u
from astropy.wcs import WCSSUB_SPECTRAL
from glue.core.message import (SubsetCreateMessage,
                               SubsetDeleteMessage,
                               SubsetUpdateMessage)
from specutils import Spectrum1D
from specutils.utils import QuantityModel
from traitlets import Bool, Int, List, Unicode
from glue.core.data import Data

from jdaviz.core.events import AddDataMessage, RemoveDataMessage, SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template
from .fitting_backend import fit_model_to_spectrum
from .initializers import initialize, model_parameters

__all__ = ['ModelFitting']

MODELS = {
     'Const1D': models.Const1D,
     'Linear1D': models.Linear1D,
     'Polynomial1D': models.Polynomial1D,
     'Gaussian1D': models.Gaussian1D,
     'Voigt1D': models.Voigt1D,
     'Lorentz1D': models.Lorentz1D
     }


@tray_registry('g-model-fitting', label="Model Fitting")
class ModelFitting(TemplateMixin):
    dialog = Bool(False).tag(sync=True)
    template = load_template("model_fitting.vue", __file__).tag(sync=True)
    dc_items = List([]).tag(sync=True)

    model_label = Unicode().tag(sync=True)
    cube_fit = Bool(False).tag(sync=True)
    temp_name = Unicode().tag(sync=True)
    temp_model = Unicode().tag(sync=True)
    model_equation = Unicode().tag(sync=True)
    eq_error = Bool(False).tag(sync=True)
    component_models = List([]).tag(sync=True)
    display_order = Bool(False).tag(sync=True)
    poly_order = Int(0).tag(sync=True)

    available_models = List(list(MODELS.keys())).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._viewer_spectra = None
        self._spectrum1d = None
        self._units = {}
        self.n_models = 0
        self._fitted_model = None
        self._fitted_spectrum = None
        self.component_models = []
        self._initialized_models = {}
        self._display_order = False
        self.model_label = "Model"
        self._selected_data_label = None
        if self.app.state.settings.get("configuration") == "cubeviz":
            self.cube_fit = True

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

    def _param_units(self, param, order=0):
        """Helper function to handle units that depend on x and y"""
        y_params = ["amplitude", "amplitude_L", "intercept"]

        if param == "slope":
            return str(u.Unit(self._units["y"]) / u.Unit(self._units["x"]))
        elif param == "poly":
            return str(u.Unit(self._units["y"]) / u.Unit(self._units["x"])**order)

        return self._units["y"] if param in y_params else self._units["x"]

    def _update_parameters_from_fit(self):
        """Insert the results of the model fit into the component_models"""
        for m in self.component_models:
            name = m["id"]
            if len(self.component_models) > 1:
                m_fit = self._fitted_model[name]
            else:
                m_fit = self._fitted_model
            temp_params = []
            for i in range(0, len(m_fit.parameters)):
                temp_param = [x for x in m["parameters"] if x["name"] ==
                              m_fit.param_names[i]]
                temp_param[0]["value"] = m_fit.parameters[i]
                temp_params += temp_param
            m["parameters"] = temp_params

        # Trick traitlets into updating the displayed values
        component_models = self.component_models
        self.component_models = []
        self.component_models = component_models

    def _update_parameters_from_QM(self):
        """
        Parse out result parameters from a QuantityModel, which isn't
        subscriptable with model name
        """
        if hasattr(self._fitted_model, "submodel_names"):
            submodel_names = self._fitted_model.submodel_names
            submodels = True
        else:
            submodel_names = [self._fitted_model.name]
            submodels = False
        fit_params = self._fitted_model.parameters
        param_names = self._fitted_model.param_names

        for i in range(len(submodel_names)):
            name = submodel_names[i]
            m = [x for x in self.component_models if x["id"] == name][0]
            temp_params = []
            if submodels:
                idxs = [j for j in range(len(param_names)) if
                        int(param_names[j][-1]) == i]
            else:
                idxs = [j for j in range(len(param_names))]
            # This is complicated by needing to handle parameter names that
            # have underscores in them, since QuantityModel adds an underscore
            # and integer to indicate to which model a parameter belongs
            for idx in idxs:
                if submodels:
                    temp_param = [x for x in m["parameters"] if x["name"] ==
                                  "_".join(param_names[idx].split("_")[0:-1])]
                else:
                    temp_param = [x for x in m["parameters"] if x["name"] ==
                                  param_names[idx]]
                temp_param[0]["value"] = fit_params[idx]
                temp_params += temp_param
            m["parameters"] = temp_params

        # Trick traitlets into updating the displayed values
        component_models = self.component_models
        self.component_models = []
        self.component_models = component_models

    def _update_initialized_parameters(self):
        # If the user changes a parameter value, we need to change it in the
        # initialized model
        for m in self.component_models:
            name = m["id"]
            for param in m["parameters"]:
                quant_param = u.Quantity(param["value"], param["unit"])
                setattr(self._initialized_models[name], param["name"],
                        quant_param)

    def _warn_if_no_equation(self):
        if self.model_equation == "" or self.model_equation is None:
            example = "+".join([m["id"] for m in self.component_models])
            snackbar_message = SnackbarMessage(
                f"Error: a model equation must be defined, e.g. {example}",
                color='error',
                sender=self)
            self.hub.broadcast(snackbar_message)
            return True
        else:
            return False

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
        # Replace NaNs from collapsed SpectralCube in Cubeviz
        # (won't affect calculations because these locations are masked)
        selected_spec.flux[np.isnan(selected_spec.flux)] = 0.0

        self._selected_data_label = event

        if self._units == {}:
            self._units["x"] = str(
                selected_spec.spectral_axis.unit)
            self._units["y"] = str(
                selected_spec.flux.unit)

        self._spectrum1d = selected_spec

    def vue_model_selected(self, event):
        # Add the model selected to the list of models
        self.temp_model = event
        if event == "Polynomial1D":
            self.display_order = True
        else:
            self.display_order = False

    def _initialize_polynomial(self, new_model):
        initialized_model = initialize(
            MODELS[self.temp_model](name=self.temp_name, degree=self.poly_order),
            self._spectrum1d.spectral_axis,
            self._spectrum1d.flux)

        self._initialized_models[self.temp_name] = initialized_model
        new_model["order"] = self.poly_order

        for i in range(self.poly_order + 1):
            param = "c{}".format(i)
            initial_val = getattr(initialized_model, param).value
            new_model["parameters"].append({"name": param,
                                            "value": initial_val,
                                            "unit": self._param_units("poly", i),
                                            "fixed": False})

        self._update_initialized_parameters()

        return new_model

    def _reinitialize_with_fixed(self):
        """
        Reinitialize all component models with current values and the
        specified parameters fixed (can't easily update fixed dictionary in
        an existing model)
        """
        temp_models = []
        for m in self.component_models:
            fixed = {}
            for p in m["parameters"]:
                fixed[p["name"]] = p["fixed"]
            # Have to initialize with fixed dictionary
            if m["model_type"] == "Polynomial1D":
                temp_model = MODELS[m["model_type"]](name=m["id"],
                                                     degree=m["order"],
                                                     fixed=fixed)
            else:
                temp_model = MODELS[m["model_type"]](name=m["id"], fixed=fixed)
            # Now we can set the parameter values
            for p in m["parameters"]:
                setattr(temp_model, p["name"], p["value"])
            temp_models.append(temp_model)
        return temp_models

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

        self._update_initialized_parameters()

    def vue_remove_model(self, event):
        self.component_models = [x for x in self.component_models
                                 if x["id"] != event]
        del(self._initialized_models[event])

    def vue_equation_changed(self, event):
        # Length is a dummy check to test the infrastructure
        if len(self.model_equation) > 20:
            self.eq_error = True

    def vue_model_fitting(self, *args, **kwargs):
        """
        Run fitting on the initialized models, fixing any parameters marked
        as such by the user, then update the displayed parameters with fit
        values
        """
        if self._warn_if_no_equation():
            return
        models_to_fit = self._reinitialize_with_fixed()

        try:
            fitted_model, fitted_spectrum = fit_model_to_spectrum(
                self._spectrum1d,
                models_to_fit,
                self.model_equation,
                run_fitter=True)
        except AttributeError:
            msg = SnackbarMessage("Unable to fit: model equation may be invalid",
                                  color="error", sender=self)
            self.hub.broadcast(msg)
            return
        self._fitted_model = fitted_model
        self._fitted_spectrum = fitted_spectrum

        self.vue_register_spectrum({"spectrum": fitted_spectrum})
        self.app.fitted_models[self.model_label] = fitted_model

        # Update component model parameters with fitted values
        if type(self._fitted_model) == QuantityModel:
            self._update_parameters_from_QM()
        else:
            self._update_parameters_from_fit()

    def vue_fit_model_to_cube(self, *args, **kwargs):

        if self._warn_if_no_equation():
            return
        data = self.app.data_collection[self._selected_data_label]

        # First, ensure that the selected data is cube-like. It is possible
        # that the user has selected a pre-existing 1d data object.
        if data.ndim != 3:
            snackbar_message = SnackbarMessage(
                f"Selected data {self._selected_data_label} is not cube-like",
                color='error',
                sender=self)
            self.hub.broadcast(snackbar_message)
            return

        # Get the primary data component
        attribute = data.main_components[0]
        component = data.get_component(attribute)
        temp_values = data.get_data(attribute)

        # Transpose the axis order
        values = np.moveaxis(temp_values, 0, -1) * u.Unit(component.units)

        # We manually create a Spectrum1D object from the flux information
        #  in the cube we select
        wcs = data.coords.sub([WCSSUB_SPECTRAL])
        spec = Spectrum1D(flux=values, wcs=wcs)

        # TODO: in vuetify >2.3, timeout should be set to -1 to keep open
        #  indefinitely
        snackbar_message = SnackbarMessage(
            "Fitting model to cube...",
            loading=True, timeout=0, sender=self)
        self.hub.broadcast(snackbar_message)

        # Retrieve copy of the models with proper "fixed" dictionaries
        # TODO: figure out why this was causing the parallel fitting to fail
        # models_to_fit = self._reinitialize_with_fixed()
        models_to_fit = self._initialized_models.values()

        fitted_model, fitted_spectrum = fit_model_to_spectrum(
            spec,
            models_to_fit,
            self.model_equation,
            run_fitter=True)

        # Save fitted 3D model in a way that the cubeviz
        # helper can access it.
        for m in fitted_model:
            temp_label = "{} ({}, {})".format(self.model_label, m["x"], m["y"])
            self.app.fitted_models[temp_label] = m["model"]

        # Transpose the axis order back
        values = np.moveaxis(fitted_spectrum.flux.value, -1, 0)

        count = max(map(lambda s: int(next(iter(re.findall(r"\d$", s)), 0)),
                        self.data_collection.labels)) + 1

        label = f"{self.model_label} [Cube] {count}"

        # Create new glue data object
        output_cube = Data(label=label,
                           coords=data.coords)
        output_cube['flux'] = values
        output_cube.get_component('flux').units = \
            fitted_spectrum.flux.unit.to_string()

        # Add to data collection
        self.app.data_collection.append(output_cube)

        snackbar_message = SnackbarMessage(
            "Finished cube fitting",
            color='success', loading=False, sender=self)
        self.hub.broadcast(snackbar_message)

    def vue_register_spectrum(self, event):
        """
        Add a spectrum to the data collection based on the currently displayed
        parameters (these could be user input or fit values).
        """
        if self._warn_if_no_equation():
            return
        # Make sure the initialized models are updated with any user-specified
        # parameters
        self._update_initialized_parameters()

        # Need to run the model fitter with run_fitter=False to get spectrum
        if "spectrum" in event:
            spectrum = event["spectrum"]
        else:
            model, spectrum = fit_model_to_spectrum(self._spectrum1d,
                                                    self._initialized_models.values(),
                                                    self.model_equation)

        self.n_models += 1
        label = self.model_label
        if label in self.data_collection:
            self.app.remove_data_from_viewer('spectrum-viewer', label)
            # Remove the actual Glue data object from the data_collection
            self.data_collection.remove(self.data_collection[label])
        self.data_collection[label] = spectrum

        self.app.add_data_to_viewer('spectrum-viewer', label)
