import re
import numpy as np

import astropy.units as u
from astropy.wcs import WCSSUB_SPECTRAL
from specutils import Spectrum1D, SpectralRegion
from specutils.utils import QuantityModel
from traitlets import Any, Bool, List, Unicode, observe
from glue.core.data import Data
from glue.core.subset import Subset, RangeSubsetState, OrState, AndState
from glue.core.link_helpers import LinkSame
from glue.core.message import SubsetDeleteMessage, SubsetUpdateMessage

from jdaviz.core.events import AddDataMessage, RemoveDataMessage, SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, SpectralSubsetSelectMixin
from jdaviz.core.custom_traitlets import IntHandleEmpty
from jdaviz.configs.default.plugins.model_fitting.fitting_backend import fit_model_to_spectrum
from jdaviz.configs.default.plugins.model_fitting.initializers import (MODELS,
                                                                       initialize,
                                                                       get_model_parameters)

__all__ = ['ModelFitting']


class _EmptyParam:
    def __init__(self, value, unit=None):
        self.value = value
        self.unit = unit
        self.quantity = u.Quantity(self.value,
                                   self.unit if self.unit is not None else u.dimensionless_unscaled)


@tray_registry('g-model-fitting', label="Model Fitting")
class ModelFitting(PluginTemplateMixin, SpectralSubsetSelectMixin):
    dialog = Bool(False).tag(sync=True)
    template_file = __file__, "model_fitting.vue"
    dc_items = List([]).tag(sync=True)
    form_valid_data_selection = Bool(False).tag(sync=True)
    form_valid_model_component = Bool(False).tag(sync=True)

    selected_data = Unicode("").tag(sync=True)

    spectral_min = Any().tag(sync=True)
    spectral_max = Any().tag(sync=True)
    spectral_unit = Unicode().tag(sync=True)

    model_label = Unicode().tag(sync=True)
    cube_fit = Bool(False).tag(sync=True)
    temp_name = Unicode().tag(sync=True)
    temp_model = Unicode().tag(sync=True)
    model_equation = Unicode().tag(sync=True)
    eq_error = Bool(False).tag(sync=True)
    component_models = List([]).tag(sync=True)
    display_order = Bool(False).tag(sync=True)
    poly_order = IntHandleEmpty(0).tag(sync=True)

    # add/replace results for "fit"
    add_replace_results = Bool(True).tag(sync=True)

    # selected_viewer for "apply to cube"
    # NOTE: this is currently cubeviz-specific so will need to be updated
    # to be config-specific if using within other viewer configurations.
    viewer_to_id = {'Left': 'cubeviz-0', 'Center': 'cubeviz-1', 'Right': 'cubeviz-2'}
    viewers = List(['None', 'Left', 'Center', 'Right']).tag(sync=True)
    selected_viewer = Unicode('None').tag(sync=True)

    available_models = List(list(MODELS.keys())).tag(sync=True)

    def __init__(self, *args, **kwargs):
        self._spectrum1d = None
        super().__init__(*args, **kwargs)

        self._units = {}
        self.n_models = 0
        self._fitted_model = None
        self._fitted_spectrum = None
        self.component_models = []
        self._initialized_models = {}
        self._display_order = False
        self.model_label = "Model"
        self._window = None
        self._original_mask = None
        if self.app.state.settings.get("configuration") == "cubeviz":
            self.cube_fit = True

        self.hub.subscribe(self, AddDataMessage,
                           handler=self._on_viewer_data_changed)
        self.hub.subscribe(self, RemoveDataMessage,
                           handler=self._on_viewer_data_changed)
        self.hub.subscribe(self, SubsetUpdateMessage,
                           handler=self._on_viewer_data_changed)
        self.hub.subscribe(self, SubsetDeleteMessage,
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
        self._viewer_id = self.app._viewer_item_by_reference(
            'spectrum-viewer').get('id')

        viewer = self.app.get_viewer('spectrum-viewer')

        self.dc_items = [layer_state.layer.label
                         for layer_state in viewer.state.layers
                         if ((not isinstance(layer_state.layer, Subset)
                              or not isinstance(layer_state.layer.subset_state,
                                                (RangeSubsetState, OrState, AndState)))
                             and layer_state.layer.label not in self.app.fitted_models.keys())]

    def _param_units(self, param, model_type=None):
        """Helper function to handle units that depend on x and y"""
        y_params = ["amplitude", "amplitude_L", "intercept", "scale"]

        if param == "slope":
            return str(u.Unit(self._units["y"]) / u.Unit(self._units["x"]))
        elif model_type == 'Polynomial1D':
            # param names are all named cN, where N is the order
            order = int(float(param[1:]))
            return str(u.Unit(self._units["y"]) / u.Unit(self._units["x"])**order)
        elif param == "temperature":
            return str(u.K)
        elif param == "scale" and model_type == "BlackBody":
            return str("")

        return self._units["y"] if param in y_params else self._units["x"]

    def _update_parameters_from_fit(self):
        """Insert the results of the model fit into the component_models"""
        for m in self.component_models:
            name = m["id"]
            if hasattr(self._fitted_model, "submodel_names"):
                if name in self._fitted_model.submodel_names:
                    m_fit = self._fitted_model[name]
                else:
                    continue
            elif self._fitted_model.name == name:
                m_fit = self._fitted_model
            else:
                # then the component was not in the fitted model
                continue
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

    @observe("selected_data")
    def _selected_data_changed(self, event):
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
                                                      data_label=event['new'])
        # Replace NaNs from collapsed Spectrum1D in Cubeviz
        # (won't affect calculations because these locations are masked)
        selected_spec.flux[np.isnan(selected_spec.flux)] = 0.0

        # Save original mask so we can reset after applying a subset mask
        self._original_mask = selected_spec.mask

        if self._units == {}:
            self._units["x"] = str(
                selected_spec.spectral_axis.unit)
            self._units["y"] = str(
                selected_spec.flux.unit)

        self._spectrum1d = selected_spec

        # Also set the spectral min and max to default to the full range
        # This is no longer needed for 1D but is preserved for now pending
        # fixes to Cubeviz for multi-subregion subsets
        self._window = None
        self.spectral_min = selected_spec.spectral_axis[0].value
        self.spectral_max = selected_spec.spectral_axis[-1].value
        self.spectral_unit = str(selected_spec.spectral_axis.unit)

    @observe("spectral_subset_selected")
    def _on_spectral_subset_selected(self, event):
        # If "Entire Spectrum" selected, reset based on bounds of selected data
        if self._spectrum1d is None:
            # TODO: this should be removed as soon as the data dropdown component is
            # created and defaults at init
            return
        if self.spectral_subset_selected == "Entire Spectrum":
            self._window = None
            self.spectral_min = self._spectrum1d.spectral_axis[0].value
            self.spectral_max = self._spectrum1d.spectral_axis[-1].value
        else:
            spec_sub = self.spectral_subset.selected_obj
            unit = u.Unit(self.spectral_unit)
            if hasattr(spec_sub, "center"):
                spreg = SpectralRegion.from_center(spec_sub.center.x * unit,
                                                   spec_sub.width * unit)
                self._window = (spreg.lower, spreg.upper)
                self.spectral_min = spreg.lower.value
                self.spectral_max = spreg.upper.value

    def vue_model_selected(self, event):
        # Add the model selected to the list of models
        self.temp_model = event
        if event == "Polynomial1D":
            self.display_order = True
        else:
            self.display_order = False

    def _reinitialize_with_fixed(self):
        """
        Reinitialize all component models with current values and the
        specified parameters fixed (can't easily update fixed dictionary in
        an existing model)
        """
        temp_models = []
        for m in self.component_models:
            fixed = {}

            # Set the initial values as quantities to make sure model units
            # are set correctly.
            initial_values = {p["name"]: u.Quantity(p["value"], p["unit"]) for p in m["parameters"]}

            for p in m["parameters"]:
                fixed[p["name"]] = p["fixed"]

            # Have to initialize with fixed dictionary
            temp_model = MODELS[m["model_type"]](name=m["id"], fixed=fixed,
                                                 **initial_values, **m.get("model_kwargs", {}))

            temp_models.append(temp_model)

        return temp_models

    def vue_add_model(self, event):
        """Add the selected model and input string ID to the list of models"""
        # validate provided label (only allow "word characters").   These should already be
        # stripped by JS in the UI element, but we'll confirm here (especially if this is ever
        # extended to have better API-support)
        if re.search(r'\W+', self.temp_name):
            raise ValueError(f"invalid model component ID {self.temp_name}")

        if self.temp_name in [cm['id'] for cm in self.component_models]:
            raise ValueError(f"model component ID {self.temp_name} already in use")

        new_model = {"id": self.temp_name, "model_type": self.temp_model,
                     "parameters": [], "model_kwargs": {}}
        model_cls = MODELS[self.temp_model]

        if self.temp_model == "Polynomial1D":
            # self.poly_order is the value in the widget for creating
            # the new model component.  We need to store that with the
            # model itself as the value could change for another component.
            new_model["model_kwargs"] = {"degree": self.poly_order}
        elif self.temp_model == "BlackBody":
            new_model["model_kwargs"] = {"output_units": self._units["y"],
                                         "bounds": {"scale": (0.0, None)}}

        initial_values = {}
        for param_name in get_model_parameters(model_cls, new_model["model_kwargs"]):
            # access the default value from the model class itself
            default_param = getattr(model_cls, param_name, _EmptyParam(0))
            default_units = self._param_units(param_name,
                                              model_type=new_model["model_type"])

            if default_param.unit is None:
                # then the model parameter accepts unitless, but we want
                # to pass with appropriate default units
                initial_val = u.Quantity(default_param.value, default_units)
            else:
                # then the model parameter has default units.  We want to pass
                # with jdaviz default units (based on x/y units) but need to
                # convert the default parameter unit to these units
                initial_val = default_param.quantity.to(default_units)

            initial_values[param_name] = initial_val

        initialized_model = initialize(
            MODELS[self.temp_model](name=self.temp_name,
                                    **initial_values,
                                    **new_model.get("model_kwargs", {})),
            self._spectrum1d.spectral_axis,
            self._spectrum1d.flux)

        # need to loop over parameters again as the initializer may have overridden
        # the original default value
        for param_name in get_model_parameters(model_cls, new_model["model_kwargs"]):
            param_quant = getattr(initialized_model, param_name)
            new_model["parameters"].append({"name": param_name,
                                            "value": param_quant.value,
                                            "unit": str(param_quant.unit),
                                            "fixed": False})

        self._initialized_models[self.temp_name] = initialized_model

        new_model["Initialized"] = True
        self.component_models = self.component_models + [new_model]

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

        # Apply mask from selected subset
        if self.spectral_subset_selected != "Entire Spectrum":
            subset_mask = self.app.get_data_from_viewer("spectrum-viewer",
                                        data_label = self.spectral_subset_selected).mask # noqa
            if self._spectrum1d.mask is None:
                self._spectrum1d.mask = subset_mask
            else:
                self._spectrum1d.mask += subset_mask

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

        self.app.fitted_models[self.model_label] = fitted_model
        self.vue_register_spectrum({"spectrum": fitted_spectrum})

        # Update component model parameters with fitted values
        if type(self._fitted_model) == QuantityModel:
            self._update_parameters_from_QM()
        else:
            self._update_parameters_from_fit()

        # Also update the _initialized_models so we can use these values
        # as the starting point for cube fitting
        self._update_initialized_parameters()

        # Reset the data mask in case we use a different subset next time
        self._spectrum1d.mask = self._original_mask

    def vue_fit_model_to_cube(self, *args, **kwargs):

        if self._warn_if_no_equation():
            return

        if self.selected_data in self.app.data_collection.labels:
            data = self.app.data_collection[self.selected_data]
        else:  # User selected some subset from spectrum viewer, just use original cube
            data = self.app.data_collection[0]

        # First, ensure that the selected data is cube-like. It is possible
        # that the user has selected a pre-existing 1d data object.
        if data.ndim != 3:
            snackbar_message = SnackbarMessage(
                f"Selected data {self.selected_data} is not cube-like",
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
        models_to_fit = self._reinitialize_with_fixed()

        try:
            fitted_model, fitted_spectrum = fit_model_to_spectrum(
                spec,
                models_to_fit,
                self.model_equation,
                run_fitter=True,
                window=self._window)
        except ValueError:
            snackbar_message = SnackbarMessage(
                "Cube fitting failed",
                color='error', loading=False, sender=self)
            self.hub.broadcast(snackbar_message)
            raise

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
        self.app.add_data(output_cube, label)
        if self.selected_viewer != 'None':
            # replace the contents in the selected viewer with the results from this plugin
            self.app.add_data_to_viewer(self.viewer_to_id.get(self.selected_viewer),
                                        label, clear_other_data=True)

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
                                                    self.model_equation,
                                                    window=self._window)

        self.n_models += 1
        label = self.model_label
        if label in self.data_collection:
            self.app.remove_data_from_viewer('spectrum-viewer', label)
            # Remove the actual Glue data object from the data_collection
            self.data_collection.remove(self.data_collection[label])

        self.app.add_data(spectrum, label)

        # Link the result spectrum to the reference data of the spectrum viewer

        ref_data = self.app.get_viewer('spectrum-viewer').state.reference_data
        data_id = ref_data.world_component_ids[0]
        model_id = self.app.session.data_collection[label].world_component_ids[0]
        self.app.session.data_collection.add_link(LinkSame(data_id, model_id))

        if self.add_replace_results:
            self.app.add_data_to_viewer('spectrum-viewer', label)
