import re
import numpy as np
from copy import deepcopy

import astropy.units as u
from specutils import Spectrum
from specutils.utils import QuantityModel
from traitlets import Bool, List, Unicode, observe

from jdaviz.configs.default.plugins.model_fitting.fitting_backend import fit_model_to_spectrum
from jdaviz.configs.default.plugins.model_fitting.initializers import (MODELS,
                                                                       initialize,
                                                                       get_model_parameters)
from jdaviz.core.events import SnackbarMessage, GlobalDisplayUnitChanged
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin,
                                        SelectPluginComponent,
                                        SpectralSubsetSelectMixin,
                                        DatasetSelectMixin,
                                        DatasetSpectralSubsetValidMixin,
                                        NonFiniteUncertaintyMismatchMixin,
                                        AutoTextField,
                                        AddResultsMixin,
                                        TableMixin,
                                        with_spinner)
from jdaviz.core.custom_traitlets import IntHandleEmpty
from jdaviz.core.user_api import PluginUserApi
from jdaviz.core.unit_conversion_utils import (all_flux_unit_conversion_equivs,
                                               flux_conversion_general)
from jdaviz.core.custom_units_and_equivs import PIX2

__all__ = ['ModelFitting']


class _EmptyParam:
    def __init__(self, value, unit=None):
        self.value = value
        self.unit = unit
        self.quantity = u.Quantity(self.value,
                                   self.unit if self.unit is not None else u.dimensionless_unscaled)


@tray_registry('g-model-fitting', label="Model Fitting", category="data:analysis")
class ModelFitting(PluginTemplateMixin, DatasetSelectMixin,
                   SpectralSubsetSelectMixin, DatasetSpectralSubsetValidMixin,
                   NonFiniteUncertaintyMismatchMixin,
                   AddResultsMixin, TableMixin):
    """
    See the :ref:`Model Fitting Plugin Documentation <specviz-model-fitting>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.close_in_tray`
    * ``cube_fit``
      Only exposed for Cubeviz.  Whether to fit the model to the cube instead of to the
      collapsed spectrum.
    * ``dataset`` (:class:`~jdaviz.core.template_mixin.DatasetSelect`):
      Dataset to fit the model.
    * ``spectral_subset`` (:class:`~jdaviz.core.template_mixin.SubsetSelect`)
    * ``model_component`` (:class:`~jdaviz.core.template_mixin.SelectPluginComponent`)
    * ``poly_order``
    * ``model_component_label`` (:class:`~jdaviz.core.template_mixin.AutoTextField`)
    * :meth:`create_model_component`
    * :meth:`remove_model_component`
    * :meth:`model_components`
    * :meth:`valid_model_components`
    * :meth:`get_model_component`
    * :meth:`set_model_component`
    * :meth:`reestimate_model_parameters`
    * ``equation`` (:class:`~jdaviz.core.template_mixin.AutoTextField`)
    * :meth:`equation_components`
    * ``add_results`` (:class:`~jdaviz.core.template_mixin.AddResults`)
    * ``residuals_calculate`` (bool)
      Whether to calculate and expose the residuals (model minus data).
    * ``residuals`` (:class:`~jdaviz.core.template_mixin.AutoTextField`)
      Label of the residuals to apply when calling :meth:`calculate_fit` if ``residuals_calculate``
      is ``True``.
    * :meth:`calculate_fit`
    * :meth:`fitted_models`
    * :meth:`get_models`
    * :meth:`get_model_parameters`
    """
    dialog = Bool(False).tag(sync=True)
    template_file = __file__, "model_fitting.vue"
    form_valid_model_component = Bool(False).tag(sync=True)

    # model components:
    model_comp_items = List().tag(sync=True)
    model_comp_selected = Unicode().tag(sync=True)
    poly_order = IntHandleEmpty(0).tag(sync=True)

    comp_label = Unicode().tag(sync=True)
    comp_label_default = Unicode().tag(sync=True)
    comp_label_auto = Bool(True).tag(sync=True)
    comp_label_invalid_msg = Unicode().tag(sync=True)

    model_equation = Unicode().tag(sync=True)
    model_equation_default = Unicode().tag(sync=True)
    model_equation_auto = Bool(True).tag(sync=True)
    model_equation_invalid_msg = Unicode().tag(sync=True)

    eq_error = Bool(False).tag(sync=True)
    component_models = List([]).tag(sync=True)
    display_order = Bool(False).tag(sync=True)

    cube_fit = Bool(False).tag(sync=True)

    # residuals (non-cube fit only)
    residuals_calculate = Bool(False).tag(sync=True)
    residuals_label = Unicode().tag(sync=True)
    residuals_label_default = Unicode().tag(sync=True)
    residuals_label_auto = Bool(True).tag(sync=True)
    residuals_label_invalid_msg = Unicode('').tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._units = {}  # string representation of display units
        self._fitted_model = None
        self._fitted_spectrum = None
        self._fitted_models = {}
        self.component_models = []
        self._initialized_models = {}
        self._display_order = False

        # description displayed under plugin title in tray
        self._plugin_description = 'Fit an analytic model to data or a subset of data.'

        # create the label first so that when model_component defaults to the first selection,
        # the label automatically defaults as well
        self.model_component_label = AutoTextField(self, 'comp_label', 'comp_label_default',
                                                   'comp_label_auto', 'comp_label_invalid_msg')

        self.model_component = SelectPluginComponent(self,
                                                     items='model_comp_items',
                                                     selected='model_comp_selected',
                                                     manual_options=list(MODELS.keys()))

        if self.config == 'cubeviz':
            # use mean whenever extracting the 1D spectrum of a cube to initialize model params
            self.dataset._spectral_extraction_function = 'Mean'
        # by default, require entries to be in spectrum-viewer (not other cubeviz images, etc)
        # in cubeviz, the cube_fit toggle will then replace this filter to filter for cubes
        self.dataset.add_filter('layer_in_spectrum_viewer')

        self.equation = AutoTextField(self, 'model_equation', 'model_equation_default',
                                      'model_equation_auto', 'model_equation_invalid_msg')

        self.residuals = AutoTextField(self, 'residuals_label', 'residuals_label_default',
                                       'residuals_label_auto', 'residuals_label_invalid_msg')

        headers = ['model', 'data_label', 'spectral_subset', 'equation']
        if self.config == 'cubeviz':
            headers += ['cube_fit']

        self.table.headers_avail = headers
        self.table.headers_visible = headers
        # when model parameters are added as columns, only show the value/unit columns by default
        # (other columns can be show in the dropdown by the user)
        self.table._new_col_visible = lambda colname: colname.split(':')[-1] not in ('fixed', 'uncert', 'std')  # noqa

        # set the filter on the viewer options
        self._update_viewer_filters()

        self.hub.subscribe(self, GlobalDisplayUnitChanged,
                           handler=self._on_global_display_unit_changed)

        self.parallel_n_cpu = None
        if self.config == "deconfigged":
            self.observe_traitlets_for_relevancy(traitlets_to_observe=['dataset_items'])

    @property
    def _default_spectrum_viewer_reference_name(self):
        return getattr(
            self.app._jdaviz_helper, '_default_spectrum_viewer_reference_name', 'spectrum-viewer'
        )

    @property
    def _default_flux_viewer_reference_name(self):
        return getattr(
            self.app._jdaviz_helper, '_default_flux_viewer_reference_name', 'flux-viewer'
        )

    @property
    def user_api(self):
        expose = ['dataset']
        if self.config == "cubeviz":
            expose += ['cube_fit']
        expose += ['spectral_subset', 'model_component', 'poly_order', 'model_component_label',
                   'model_components', 'valid_model_components',
                   'create_model_component', 'remove_model_component',
                   'get_model_component', 'set_model_component', 'reestimate_model_parameters',
                   'equation', 'equation_components',
                   'add_results', 'residuals_calculate', 'residuals']
        expose += ['calculate_fit', 'clear_table', 'export_table',
                   'fitted_models', 'get_models', 'get_model_parameters']
        return PluginUserApi(self, expose=expose)

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
            submodel_index = None
            name = m["id"]
            if hasattr(self._fitted_model, "submodel_names"):
                for i in range(len(self._fitted_model.submodel_names)):
                    if name == self._fitted_model.submodel_names[i]:
                        m_fit = self._fitted_model[name]
                        submodel_index = i
                if submodel_index is None:
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
                # The submodels don't have uncertainties attached, only the compound model
                if self._fitted_model.stds is not None:
                    std_name = temp_param[0]["name"]
                    if submodel_index is not None:
                        std_name = f"{std_name}_{submodel_index}"
                    if std_name in self._fitted_model.stds.param_names:
                        temp_param[0]["std"] = self._fitted_model.stds[std_name]

                temp_params += temp_param

            m["parameters"] = temp_params

        self.send_state('component_models')

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

        self.send_state('component_models')

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

    def _update_viewer_filters(self, event={}):
        if event.get('new', self.cube_fit):
            # only want image viewers in the options
            self.add_results.viewer.filters = ['is_image_viewer']
        else:
            # only want spectral viewers in the options
            self.add_results.viewer.filters = ['is_spectrum_viewer']

    @observe('cube_fit')
    def _cube_fit_changed(self, event={}):
        self._update_viewer_filters(event=event)

        sb_unit = self.app._get_display_unit('sb')
        spectral_y_unit = self.app._get_display_unit('spectral_y')
        if event.get('new'):
            self._units['y'] = str(sb_unit)
            self.dataset.add_filter('is_flux_cube')
            self.dataset.remove_filter('layer_in_spectrum_viewer')
        else:
            self._units['y'] = str(spectral_y_unit)
            self.dataset.add_filter('layer_in_spectrum_viewer')
            self.dataset.remove_filter('is_flux_cube')

        self.dataset._clear_cache()
        if sb_unit != spectral_y_unit:
            # We make the user hit the reestimate button themselves
            for model_index, comp_model in enumerate(self.component_models):
                self.component_models[model_index]["compat_display_units"] = False
            self.send_state('component_models')

    @observe("dataset_selected")
    def _dataset_selected_changed(self, event=None):
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
        if not hasattr(self, 'dataset') or self.app._jdaviz_helper is None or self.dataset_selected == '':  # noqa
            # during initial init, this can trigger before the component is initialized
            return

        selected_spec = self.dataset.selected_obj
        if selected_spec is None:
            return

        # Replace NaNs from collapsed Spectrum in Cubeviz
        # (won't affect calculations because these locations are masked)
        selected_spec.flux[np.isnan(selected_spec.flux)] = 0.0

    def _default_comp_label(self, model, poly_order=None):
        abbrevs = {'BlackBody': 'BB', 'PowerLaw': 'PL', 'Lorentz1D': 'Lo'}
        abbrev = abbrevs.get(model, model[0].upper())
        if model == "Polynomial1D":
            abbrev += f'{poly_order}'

        # append a number suffix to avoid any duplicates
        ind = 1
        while abbrev in [cm['id'] for cm in self.component_models]:
            abbrev = f'{abbrev.split("_")[0]}_{ind}'
            ind += 1

        return abbrev

    @observe('model_comp_selected', 'poly_order')
    def _update_comp_label_default(self, event={}):
        self.display_order = self.model_comp_selected == "Polynomial1D"
        self.comp_label_default = self._default_comp_label(self.model_comp_selected,
                                                           self.poly_order)

    @observe('comp_label')
    def _comp_label_changed(self, event={}):
        if not len(self.comp_label.strip()):
            # strip will raise the same error for a label of all spaces
            self.comp_label_invalid_msg = 'label must be provided'
            return
        if self.comp_label in [cm['id'] for cm in self.component_models]:
            self.comp_label_invalid_msg = 'label already in use'
            return
        self.comp_label_invalid_msg = ''

    def _update_model_equation_default(self):
        self.model_equation_default = '+'.join(cm['id'] for cm in self.component_models)

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

    def create_model_component(self, model_component=None, model_component_label=None,
                               poly_order=None):
        """
        Add a new model component to the list of available model components

        Parameters
        ----------
        model_component : str
            Type of model component to add.  If not provided, will default according to
            ``model_component``.
        model_component_label : str
            Name of the model component to add.  If not provided, will default according to
            ``model_component_label`` (if ``model_component_label.auto`` is True and
            ``model_component`` is passed as an argument, then the default label will be recomputed
            rather than applying the current value).
        poly_order : int
            Order of the polynomial if ``model_component`` is (or defaults to) "Polynomial1D".
            Will raise an error if provided and ``model_component`` is not "Polynomial1D".
            If not provided, will default according to ``poly_order``.
        """
        model_comp = model_component if model_component is not None else self.model_comp_selected

        if model_comp != "Polynomial1D" and poly_order is not None:
            raise ValueError("poly_order should only be passed if model_component is Polynomial1D")
        poly_order = poly_order if poly_order is not None else self.poly_order

        # if model_component was passed and different than the one set in the traitlet, AND
        # model_component_label is not passed, AND the auto is enabled on the label, then
        # recompute a temporary default model label rather than use the value set in the traitlet
        if model_comp != self.model_comp_selected and model_component_label is None and self.model_component_label.auto:  # noqa
            comp_label = self._default_comp_label(model_comp, poly_order)
        else:
            comp_label = model_component_label if model_component_label is not None else self.comp_label  # noqa

        # validate provided label (only allow "word characters").   These should already be
        # stripped by JS in the UI element, but we'll confirm here (especially if this is ever
        # extended to have better API-support)
        if re.search(r'\W+', comp_label) or not len(comp_label):
            raise ValueError(f"invalid model component label '{comp_label}'")

        if comp_label in [cm['id'] for cm in self.component_models]:
            raise ValueError(f"model component label '{comp_label}' already in use")

        new_model = self._initialize_model_component(model_comp, comp_label, poly_order=poly_order)
        self.component_models = self.component_models + [new_model]
        # update the default label (likely adding the suffix)
        self._update_comp_label_default()
        self._update_model_equation_default()

    def _initialize_model_component(self, model_comp, comp_label, poly_order=None):
        new_model = {"id": comp_label, "model_type": model_comp,
                     "parameters": [], "model_kwargs": {}}
        model_cls = MODELS[model_comp]

        # Need to set the units the first time we initialize a model component, after this
        # we listen for display unit changes
        if self._units.get('x', '') == '':
            self._units['x'] = str(self.app._get_display_unit('spectral'))
        if self._units.get('y', '') == '':
            if self.cube_fit:
                self._units['y'] = str(self.app._get_display_unit('sb'))
            else:
                self._units['y'] = str(self.app._get_display_unit('spectral_y'))

        if model_comp == "Polynomial1D":
            # self.poly_order is the value in the widget for creating
            # the new model component.  We need to store that with the
            # model itself as the value could change for another component.
            new_model["model_kwargs"] = {"degree": poly_order}
        elif model_comp == "BlackBody":
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
                if default_param.unit != default_units:
                    pixar_sr = self.app.data_collection[0].meta.get('PIXAR_SR', 1)
                    viewer = self.app.get_viewer("spectrum-viewer")
                    # TODO: I suspect this doesn't actually work, but never gets called -Ricky
                    cube_wave = viewer.slice_value * u.Unit(self.app._get_display_unit('spectral'))
                    equivs = all_flux_unit_conversion_equivs(pixar_sr, cube_wave)

                    initial_val = flux_conversion_general([default_param.value],
                                                          default_param.unit,
                                                          default_units, equivs)
                else:
                    initial_val = default_param

            initial_values[param_name] = initial_val

        if self.cube_fit:
            # We need to input the whole cube when initializing the model so the units are correct.
            if self.dataset_selected in self.app.data_collection.labels:
                data = self.app.data_collection[self.dataset_selected].get_object(statistic=None)
            else:  # User selected some subset from spectrum viewer, just use original cube
                data = self.app.data_collection[0].get_object(statistic=None)
            spatial_axes = [0, 1, 2]
            spatial_axes.remove(data.spectral_axis_index)
            masked_spectrum = self._apply_subset_masks(data, self.spectral_subset,
                                                       spatial_axes=tuple(spatial_axes))
        else:
            masked_spectrum = self._apply_subset_masks(self.dataset.selected_spectrum,
                                                       self.spectral_subset)

        mask = masked_spectrum.mask
        if mask is not None:
            if mask.ndim == 3:
                if masked_spectrum.spectral_axis_index in [2, -1]:
                    spectral_mask = mask.all(axis=(0, 1))
                elif masked_spectrum.spectral_axis_index == 0:
                    spectral_mask = mask.all(axis=(1, 2))
            else:
                spectral_mask = mask
            init_x = masked_spectrum.spectral_axis[~spectral_mask]
            orig_flux_shape = masked_spectrum.flux.shape
            init_y = masked_spectrum.flux[~mask]
            if mask.ndim == 3:
                if masked_spectrum.spectral_axis_index in [2, -1]:
                    init_y = init_y.reshape(orig_flux_shape[0],
                                            orig_flux_shape[1],
                                            len(init_x))
                elif masked_spectrum.spectral_axis_index == 0:
                    init_y = init_y.reshape(len(init_x),
                                            orig_flux_shape[1],
                                            orig_flux_shape[2])
        else:
            init_x = masked_spectrum.spectral_axis
            init_y = masked_spectrum.flux

        if init_y.unit != self._units['y']:
            # equivs for spectral density and flux<>sb
            pixar_sr = masked_spectrum.meta.get('_pixel_scale_factor', 1.0)
            equivs = all_flux_unit_conversion_equivs(pixar_sr, init_x.mean())

            init_y = flux_conversion_general(init_y.value,
                                             init_y.unit,
                                             self._units['y'],
                                             equivs)

        # We need this for models where we average over the spatial axes to initialize
        spectral_axis_index = masked_spectrum.spectral_axis_index

        initialized_model = initialize(
            MODELS[model_comp](name=comp_label,
                               **initial_values,
                               **new_model.get("model_kwargs", {})),
            init_x, init_y, spectral_axis_index=spectral_axis_index)

        # need to loop over parameters again as the initializer may have overridden
        # the original default value. However, if we toggled cube_fit, we may need to override
        for param_name in get_model_parameters(model_cls, new_model["model_kwargs"]):
            param_quant = getattr(initialized_model, param_name)
            new_model["parameters"].append({"name": param_name,
                                            "value": param_quant.value,
                                            "unit": str(param_quant.unit),
                                            "fixed": False})
        self._initialized_models[comp_label] = initialized_model

        new_model["Initialized"] = True
        new_model["initialized_display_units"] = self._units.copy()

        new_model["compat_display_units"] = True  # always compatible at time of creation
        return new_model

    def _check_model_component_compat(self, axes=['x', 'y'], display_units=None):
        if display_units is None:
            display_units = [u.Unit(self._units[ax]) for ax in axes]

        disp_physical_types = [unit.physical_type for unit in display_units]

        for model_index, comp_model in enumerate(self.component_models):
            compat = True
            for ax, ax_physical_type in zip(axes, disp_physical_types):
                comp_unit = u.Unit(comp_model["initialized_display_units"][ax])
                compat = comp_unit.physical_type == ax_physical_type
                if not compat:
                    break
            self.component_models[model_index]["compat_display_units"] = compat

        # length hasn't changed, so we need to force the traitlet to update
        self.send_state("component_models")
        self._check_model_equation_invalid()

    def _on_global_display_unit_changed(self, msg):
        if msg.axis in ('spectral_y', 'sb', 'flux'):
            axis = 'y'
        elif msg.axis == 'spectral':
            axis = 'x'
        else:
            return

        unit = msg.unit

        if axis == 'y':
            # The units have to be in surface brightness for a cube fit.
            uc = self.app._jdaviz_helper.plugins.get('Unit Conversion', None)
            if uc is None:
                return
            if not self.cube_fit:
                # use spectrum viewer y axis units
                if hasattr(uc, 'spectral_y_unit'):
                    # NOTE, spectral_y_unit should probably be set and exposed
                    # in the unit conversion plugin for specviz2d
                    # and specviz so this check doesn't have to be done
                    unit = u.Unit(uc.spectral_y_unit)
                else:
                    unit = u.Unit(self.app._get_display_unit('spectral_y'))

            else:
                if unit != uc._obj.sb_unit_selected:
                    self._units[axis] = uc._obj.sb_unit_selected
                    self._check_model_component_compat([axis], [u.Unit(uc._obj.sb_unit_selected)])
                    return
                elif msg.axis == 'flux' and uc._obj.has_sb:
                    unit = u.Unit(self.app._get_display_unit('sb'))

        # update internal tracking of current units
        self._units[axis] = str(unit)

        self._check_model_component_compat([axis], [unit])

    def remove_model_component(self, model_component_label):
        """
        Remove an existing model component.

        Parameters
        ----------
        model_component_label : str
            The label given to the existing model component
        """
        if model_component_label not in [x["id"] for x in self.component_models]:
            raise ValueError(f"model component with label '{model_component_label}' does not exist")

        self.component_models = [x for x in self.component_models
                                 if x["id"] != model_component_label]
        del self._initialized_models[model_component_label]
        self._update_comp_label_default()
        self._update_model_equation_default()

    def get_model_component(self, model_component_label, parameter=None):
        """
        Get a (read-only) dictionary representation of an existing model component.

        Parameters
        ----------
        model_component_label : str
            The label given to the existing model component
        parameter : str
            Optional.  The name of a valid parameter in the model component, in which case only
            the information on that parameter is returned.
        """
        try:
            model_component = [x for x in self.component_models
                               if x["id"] == model_component_label][0]
        except IndexError:
            raise ValueError(f"'{model_component_label}' is not a label of an existing model component")  # noqa

        comp = {"model_type": model_component['model_type'],
                "parameters": {p['name']: {'value': p['value'],
                                           'unit': p['unit'],
                                           'std': p.get('std', np.nan),
                                           'fixed': p['fixed']} for p in model_component['parameters']}}  # noqa

        if parameter is not None:
            return comp['parameters'].get(parameter)
        return comp

    def set_model_component(self, model_component_label, parameter, value=None, fixed=None):
        """
        Set the value or fixed attribute of a parameter in an existing model component.

        Parameters
        ----------
        model_component_label : str
            The label given to the existing model component
        parameter : str
            The name of a valid parameter in the model component.
        value : float
            Optional.  The new initial value of the parameter.  If not provided or None, will
            remain unchanged.
        fixed : bool
            Optional.  The new state of the fixed attribute of the parameter.  If not provided
            or None, will remain unchanged.

        Returns
        -------
        updated dictionary of the parameter representation
        """
        cms = self.component_models
        try:
            model_component = [x for x in cms if x["id"] == model_component_label][0]
        except IndexError:
            raise ValueError(f"'{model_component_label}' is not a label of an existing model component")  # noqa
        try:
            parameter = [p for p in model_component['parameters'] if p['name'] == parameter][0]
        except IndexError:
            raise ValueError(f"'{parameter}' is not the name of a parameter in the '{model_component_label}' model component")  # noqa

        if value is not None:
            if not isinstance(value, (int, float)):
                raise TypeError("value must be a float")
            parameter['value'] = value
        if fixed is not None:
            if not isinstance(fixed, bool):
                raise TypeError("fixed must be a boolean")
            parameter['fixed'] = fixed

        self.component_models = []
        self.component_models = cms

        return parameter

    def vue_reestimate_model_parameters(self, model_component_label=None, **kwargs):
        self.reestimate_model_parameters(model_component_label=model_component_label)

    def reestimate_model_parameters(self, model_component_label=None):
        """
        Re-estimate all free parameters in a given model component given the currently selected
        data and subset selections.

        Parameters
        ----------
        model_component_label : str or None.
            The label given to the existing model component.  If None, will iterate over all model
            components.
        """
        if model_component_label is None:
            return [self.reestimate_model_parameters(model_comp["id"])
                    for model_comp in self.component_models]

        try:
            model_index, model_comp = [(i, x) for i, x in enumerate(self.component_models)
                                       if x["id"] == model_component_label][0]
        except IndexError:
            raise ValueError(f"'{model_component_label}' is not a label of an existing model component")  # noqa

        # store user-fixed parameters so we can revert after re-initializing
        fixed_params = {p['name']: p for p in model_comp['parameters'] if p['fixed']}

        new_model = self._initialize_model_component(model_comp['model_type'],
                                                     model_component_label,
                                                     poly_order=model_comp['model_kwargs'].get('degree', None))  # noqa

        # revert fixed parameters to user-value
        new_model['parameters'] = [fixed_params.get(p['name'], p) for p in new_model['parameters']]

        self.component_models[model_index] = new_model
        # length hasn't changed, so we need to force the traitlet to update
        self.send_state("component_models")

        # model units may have changed, need to re-check their compatibility with display units
        self._check_model_component_compat()

        # return user-friendly info on revised model
        return self.get_model_component(model_component_label)

    @property
    def model_components(self):
        """
        List of the labels of existing model components
        """
        return [x["id"] for x in self.component_models]

    @property
    def valid_model_components(self):
        """
        List of the labels of existing valid (due to display units) model components
        """
        return [x["id"] for x in self.component_models if x["compat_display_units"]]

    @property
    def equation_components(self):
        """
        List of the labels of model components in the current equation
        """
        return re.split(r'[+*/-]', self.equation.value.replace(' ', ''))

    @property
    def fitted_models(self):
        """
        Dictionary of all previously fitted models.
        """
        return self._fitted_models

    def get_models(self, models=None, model_label=None, x=None, y=None):
        """
        Loop through all models and output models of the label model_label.
        If x or y is set, return model_labels of those (x, y) coordinates.
        If x and y are None, print all models regardless of coordinates.

        Parameters
        ----------
        models : dict
            A dict of models, with the key being the label name and the value
            being an `astropy.modeling.CompoundModel` object. Defaults to
            `fitted_models` if no parameter is provided.
        model_label : str
            The name of the model that will be found and returned. If it
            equals default, every model present will be returned.
        x : int
            The x coordinate of the model spaxels that will be returned.
        y : int
            The y coordinate of the model spaxels that will be returned.

        Returns
        -------
        selected_models : dict
            Dictionary of the selected models.
        """
        selected_models = {}
        # If models is not provided, use the app's fitted models
        if not models:
            models = self.fitted_models

        # Loop through all keys in the dict models
        for label in models:
            # Prevent "Model 2" from being returned when model_label is "Model"
            if model_label is not None:
                if label.split(" (")[0] != model_label:
                    continue

            # If no label was provided, use label name without coordinates.
            if model_label is None and " (" in label:
                find_label = label.split(" (")[0]
            # If coordinates are not present, just use the label.
            elif model_label is None:
                find_label = label
            else:
                find_label = model_label

            # If x and y are set, return keys that match the model plus that
            # coordinate pair. If only x or y is set, return keys that fit
            # that value for the appropriate coordinate.
            if x is not None and y is not None:
                find_label = r"{} \({}, {}\)".format(find_label, x, y)
            elif x:
                find_label = r"{} \({}, .+\)".format(find_label, x)
            elif y:
                find_label = r"{} \(.+, {}\)".format(find_label, y)

            if re.search(find_label, label):
                selected_models[label] = models[label]

        return selected_models

    def _get_model_parameters(self, models=None, model_label=None, x=None, y=None):
        """
        Convert each parameter of model inside models into a coordinate that
        maps the model name and parameter name to a `astropy.units.Quantity`
        object.

        Parameters
        ----------
        models : dict
            A dictionary where the key is a model name and the value is an
            `astropy.modeling.CompoundModel` object.
        model_label : str
            Get model parameters for a particular model by inputting its label.
        x : int
            The x coordinate of the model spaxels that will be returned from
            get_models.
        y : int
            The y coordinate of the model spaxels that will be returned from
            get_models.

        Returns
        -------
        :dict: a dictionary of the form
            {model name: {parameter name: [[`astropy.units.Quantity`]]}}
            for 3d models or
            {model name: {parameter name: `astropy.units.Quantity`}} where the
            Quantity object represents the parameter value and unit of one of
            spaxel models or the 1d models, respectively.
        """
        if models and model_label:
            models = self.get_models(models=models, model_label=model_label, x=x, y=y)
        elif models is None and model_label:
            models = self.get_models(model_label=model_label, x=x, y=y)
        elif models is None:
            models = self.fitted_models

        data_shapes = {}
        for label in models:
            data_label = label.split(" (")[0]
            if data_label not in data_shapes:
                data_shapes[data_label] = self.app.data_collection[data_label].data.shape

        param_dict = {}
        parameters_cube = {}
        param_x_y = {}
        param_units = {}

        for label in models:
            # 3d models take the form of "Model (1,2)" so this if statement
            # looks for that style and separates out the pertinent information.
            if " (" in label:
                label_split = label.split(" (")
                model_name = label_split[0]
                x = int(label_split[1].split(", ")[0])
                y = int(label_split[1].split(", ")[1][:-1])

                # x and y values are added to this dict where they will be used
                # to convert the models of each spaxel into a single
                # coordinate in the parameters_cube dictionary.
                if model_name not in param_x_y:
                    param_x_y[model_name] = {'x': [], 'y': []}
                if x not in param_x_y[model_name]['x']:
                    param_x_y[model_name]['x'].append(x)
                if y not in param_x_y[model_name]['y']:
                    param_x_y[model_name]['y'].append(y)

            # 1d models will be handled by this else statement.
            else:
                model_name = label

            if model_name not in param_dict:
                param_dict[model_name] = list(models[label].param_names)

        # This adds another dictionary as the value of
        # parameters_cube[model_name] where the key is the parameter name
        # and the value is either a 2d array of zeros or a single value, depending
        # on whether the model in question is 3d or 1d, respectively.
        for model_name in param_dict:
            if model_name in param_x_y:
                parameters_cube[model_name] = {x: np.zeros(shape=data_shapes[model_name][:2])
                                               for x in param_dict[model_name]}
            else:
                parameters_cube[model_name] = {x: 0
                                               for x in param_dict[model_name]}

        # This loop handles the actual placement of param.values and
        # param.units into the parameter_cubes dictionary.
        for label in models:
            if " (" in label:
                label_split = label.split(" (")
                model_name = label_split[0]

                # If the get_models method is used to build a dictionary of
                # models and a value is set for the x or y parameters, that
                # will mean that only one x or y value is present in the
                # models.
                if len(param_x_y[model_name]['x']) == 1:
                    x = 0
                else:
                    x = int(label_split[1].split(", ")[0])

                if len(param_x_y[model_name]['y']) == 1:
                    y = 0
                else:
                    y = int(label_split[1].split(", ")[1][:-1])

                param_units[model_name] = {}

                for name in param_dict[model_name]:
                    param = getattr(models[label], name)
                    parameters_cube[model_name][name][x][y] = param.value
                    param_units[model_name][name] = param.unit
            else:
                model_name = label
                param_units[model_name] = {}

                # 1d models do not have anything set of param.unit, so the
                # return_units and input_units properties need to be used
                # instead, depending on the type of parameter `name` is.
                for name in param_dict[model_name]:
                    param = getattr(models[label], name)
                    parameters_cube[model_name][name] = param.value
                    param_units[model_name][name] = param.unit

        # Convert values of parameters_cube[key][param_name] into u.Quantity
        # objects that contain the appropriate unit set in
        # param_units[key][param_name]
        for key in parameters_cube:
            for param_name in parameters_cube[key]:
                parameters_cube[key][param_name] = u.Quantity(
                    parameters_cube[key][param_name],
                    param_units[key].get(param_name, None))

        return parameters_cube

    def get_model_parameters(self, model_label=None, x=None, y=None):
        """
        Convert each parameter of model inside models into a coordinate that
        maps the model name and parameter name to a `astropy.units.Quantity`
        object.

        Parameters
        ----------
        model_label : str
            Get model parameters for a particular model by inputting its label.
        x : int
            The x coordinate of the model spaxels that will be returned from
            get_models.
        y : int
            The y coordinate of the model spaxels that will be returned from
            get_models.

        Returns
        -------
        :dict: a dictionary of the form
            {model name: {parameter name: [[`astropy.units.Quantity`]]}}
            for 3d models or
            {model name: {parameter name: `astropy.units.Quantity`}} where the
            Quantity object represents the parameter value and unit of one of
            spaxel models or the 1d models, respectively.
        """
        return self._get_model_parameters(models=None, model_label=model_label,
                                          x=x, y=y)

    def vue_add_model(self, event):
        self.create_model_component()

    def vue_remove_model(self, event):
        self.remove_model_component(event)

    @observe('model_equation')
    def _check_model_equation_invalid(self, event=None):
        # Length is a dummy check to test the infrastructure
        if len(self.model_equation) == 0:
            self.model_equation_invalid_msg = 'model equation is required.'
            return
        if '' in self.equation_components:
            # includes an operator without a variable (ex: 'C+')
            self.model_equation_invalid_msg = 'incomplete equation.'
            return

        components_not_existing = [comp for comp in self.equation_components
                                   if comp not in self.model_components]
        if len(components_not_existing):
            if len(components_not_existing) == 1:
                msg = "is not an existing model component."
            else:
                msg = "are not existing model components."
            self.model_equation_invalid_msg = f'{", ".join(components_not_existing)} {msg}'
            return
        components_not_valid = [comp for comp in self.equation_components
                                if comp not in self.valid_model_components]
        if len(components_not_valid):
            if len(components_not_valid) == 1:
                msg = ("is currently disabled because it has"
                       " incompatible units with the current display units."
                       " Remove the component from the equation,"
                       " re-estimate its free parameters to use the new units"
                       " or revert the display units.")
            else:
                msg = ("are currently disabled because they have"
                       " incompatible units with the current display units."
                       " Remove the components from the equation,"
                       " re-estimate their free parameters to use the new units"
                       " or revert the display units.")
            self.model_equation_invalid_msg = f'{", ".join(components_not_valid)} {msg}'
            return
        self.model_equation_invalid_msg = ''

    @observe("dataset_selected", "dataset_items", "cube_fit")
    def _set_default_results_label(self, event={}):
        label_comps = []
        if hasattr(self, 'dataset') and (len(self.dataset.labels) > 1 or self.app.config == 'mosviz'):  # noqa
            label_comps += [self.dataset_selected]
        label_comps += ["model"]
        self.results_label_default = " ".join(label_comps)

    @observe("results_label")
    def _set_residuals_label_default(self, event={}):
        self.residuals_label_default = self.results_label+" residuals"

    @with_spinner()
    def calculate_fit(self, add_data=True):
        """
        Calculate the fit.

        Parameters
        ----------
        add_data : bool
            Whether to add the resulting spectrum/cube to the app as a data entry according to
            ``add_results``.

        Returns
        -------
        fitted model
        fitted spectrum/cube
        residuals (if ``residuals_calculate`` is set to ``True``)
        """

        if not self.spectral_subset_valid:
            valid, spec_range, subset_range = self._check_dataset_spectral_subset_valid(return_ranges=True)  # noqa
            raise ValueError(f"spectral subset '{self.spectral_subset.selected}' {subset_range} is outside data range of '{self.dataset.selected}' {spec_range}")  # noqa
        if len(self.model_equation_invalid_msg):
            raise ValueError(f"model equation is invalid: {self.model_equation_invalid_msg}")

        if self.cube_fit:
            ret = self._fit_model_to_cube(add_data=add_data)
        else:
            ret = self._fit_model_to_spectrum(add_data=add_data)

        if ret is None:  # pragma: no cover
            # something went wrong in the fitting call and (hopefully) already raised a warning,
            # but we don't have anything to add to the table
            return ret

        if self.cube_fit:
            # cube fits are currently unsupported in tables
            return ret

        row = {'model': self.results_label if add_data else '',
               'data_label': self.dataset_selected,
               'spectral_subset': self.spectral_subset_selected,
               'equation': self.equation.value}

        equation_components = self.equation_components
        for comp_ind, comp in enumerate(equation_components):
            for param_name, param_dict in self.get_model_component(comp).get('parameters', {}).items():  # noqa
                colprefix = f"{comp}:{param_name}_{comp_ind}"
                row[colprefix] = param_dict.get('value')
                row[f"{colprefix}:unit"] = param_dict.get('unit')
                row[f"{colprefix}:fixed"] = param_dict.get('fixed')
                row[f"{colprefix}:std"] = param_dict.get('std')

        self.table.add_item(row)

        return ret

    def vue_apply(self, event):
        self.calculate_fit()

    def _fit_model_to_spectrum(self, add_data):
        """
        Run fitting on the initialized models, fixing any parameters marked
        as such by the user, then update the displayed parameters with fit
        values
        """
        if self._warn_if_no_equation():
            return
        models_to_fit = self._reinitialize_with_fixed()

        spec = self.dataset.get_selected_spectrum(use_display_units=True)

        masked_spectrum = self._apply_subset_masks(spec,
                                                   self.spectral_subset)

        try:
            fitted_model, fitted_spectrum = fit_model_to_spectrum(
                masked_spectrum,
                models_to_fit,
                self.model_equation,
                run_fitter=True,
                window=None,
                n_cpu=self.parallel_n_cpu,
            )
        except AttributeError:
            msg = SnackbarMessage("Unable to fit: model equation may be invalid",
                                  color="error", sender=self)
            self.hub.broadcast(msg)
            return

        selected_spec = self.dataset.selected_obj
        if '_pixel_scale_factor' in selected_spec.meta:
            fitted_spectrum.meta['_pixel_scale_factor'] = selected_spec.meta['_pixel_scale_factor']

        self._fitted_model = fitted_model
        self._fitted_spectrum = fitted_spectrum

        if add_data:
            self._fitted_models[self.results_label] = fitted_model
            self.add_results.add_results_from_plugin(fitted_spectrum)

            if self.residuals_calculate:
                # NOTE: this will NOT load into the viewer since we have already called
                # add_results_from_plugin above.
                self.add_results.add_results_from_plugin(masked_spectrum-fitted_spectrum,
                                                         label=self.residuals.value,
                                                         replace=False)

        self._set_default_results_label()

        # Update component model parameters with fitted values
        if isinstance(self._fitted_model, QuantityModel):
            self._update_parameters_from_QM()
        else:
            self._update_parameters_from_fit()

        # Also update the _initialized_models so we can use these values
        # as the starting point for cube fitting
        self._update_initialized_parameters()

        if self.residuals_calculate:
            return fitted_model, fitted_spectrum, masked_spectrum-fitted_spectrum
        return fitted_model, fitted_spectrum

    def _fit_model_to_cube(self, add_data):

        if self._warn_if_no_equation():
            return

        if self.dataset_selected in self.app.data_collection.labels:
            data = self.app.data_collection[self.dataset_selected]
        else:  # User selected some subset from spectrum viewer, just use original cube
            data = self.app.data_collection[0]

        # First, ensure that the selected data is cube-like. It is possible
        # that the user has selected a pre-existing 1d data object.
        if data.ndim != 3:
            snackbar_message = SnackbarMessage(
                f"Selected data {self.dataset_selected} is not cube-like",
                color='error',
                sender=self)
            self.hub.broadcast(snackbar_message)
            return

        # Get the primary data component
        if "_orig_spec" in data.meta:
            spec = data.meta["_orig_spec"]
        else:
            spec = data.get_object(cls=Spectrum, statistic=None)

        spatial_axes = [0, 1, 2]
        spatial_axes.remove(spec.spectral_axis_index)

        sb_unit = self.app._get_display_unit('sb')
        if spec.flux.unit != sb_unit:
            # ensure specutils has access to jdaviz custom unit equivalencies
            pixar_sr = spec.meta.get('_pixel_scale_factor', None)
            equivalencies = all_flux_unit_conversion_equivs(pixar_sr=pixar_sr,
                                                            cube_wave=spec.spectral_axis.mean())

            pix2_in_flux = 'pix2' in spec.flux.unit.to_string()
            pix2_in_sb = 'pix2' in sb_unit
            # Handle various cases when PIX2 angle unit is present in the conversion
            if pix2_in_flux and pix2_in_sb:
                spec = spec.with_flux_unit(u.Unit(spec.flux.unit)*PIX2, equivalencies=equivalencies)  # noqa
                spec = spec.with_flux_unit(u.Unit(sb_unit)*PIX2, equivalencies=equivalencies)
            elif pix2_in_flux:
                spec = spec.with_flux_unit(u.Unit(spec.flux.unit) * PIX2, equivalencies=equivalencies)  # noqa
            elif pix2_in_sb:
                spec = spec.with_flux_unit(u.Unit(spec.flux.unit) / PIX2, equivalencies=equivalencies)  # noqa

            spec = spec.with_flux_unit(sb_unit, equivalencies=equivalencies)

        snackbar_message = SnackbarMessage(
            "Fitting model to cube...",
            loading=True, sender=self)
        self.hub.broadcast(snackbar_message)

        # Retrieve copy of the models with proper "fixed" dictionaries
        models_to_fit = self._reinitialize_with_fixed()

        # Apply masks from selected spectral subset
        spec = self._apply_subset_masks(spec, self.spectral_subset, spatial_axes=spatial_axes)
        # Also mask out NaNs for fitting. Simply adding filter_non_finite to the cube fit
        # didn't work out of the box, so doing this for now.
        if spec.mask is None:
            spec.mask = np.isnan(spec.flux)
        else:
            spec.mask = spec.mask | np.isnan(spec.flux)

        try:
            fitted_model, fitted_spectrum = fit_model_to_spectrum(
                spec,
                models_to_fit,
                self.model_equation,
                run_fitter=True,
                window=None,
                n_cpu=self.parallel_n_cpu
            )
        except ValueError:
            snackbar_message = SnackbarMessage(
                "Cube fitting failed",
                color='error', loading=False, sender=self)
            self.hub.broadcast(snackbar_message)
            raise

        # Save fitted 3D model in a way that the cubeviz
        # helper can access it.
        if add_data:
            for m in fitted_model:
                temp_label = "{} ({}, {})".format(self.results_label, m["x"], m["y"])
                self._fitted_models[temp_label] = m["model"]

        output_cube = Spectrum(flux=fitted_spectrum.flux, wcs=fitted_spectrum.wcs)

        selected_spec = self.dataset.selected_obj
        if '_pixel_scale_factor' in selected_spec.meta:
            output_cube.meta['_pixel_scale_factor'] = selected_spec.meta['_pixel_scale_factor']

        # Create new data entry for glue
        if add_data:
            self.add_results.add_results_from_plugin(output_cube)
            self._set_default_results_label()

        snackbar_message = SnackbarMessage(
            "Finished cube fitting",
            color='success', loading=False, sender=self)
        self.hub.broadcast(snackbar_message)

        return fitted_model, output_cube

    def _apply_subset_masks(self, spectrum, subset_component, spatial_axes=None):
        """
        For a spectrum/spectral cube ``spectrum``, add a mask attribute
        if none exists. Mask excludes non-selected spectral subsets.
        """
        # only look for a mask if there is a selected subset:
        if subset_component.selected == subset_component.default_text:
            return spectrum

        spectrum = deepcopy(spectrum)
        subset_mask = subset_component.selected_subset_mask

        if spectrum.mask is not None:
            if subset_mask.ndim == 3:
                if spectrum.mask.ndim == 1:
                    # if subset mask is 3D and the `spectrum` mask is 1D, which
                    # happens when `spectrum` has been collapsed from 3D->1D,
                    # then also collapse the 3D mask in the spatial
                    # dimensions so that slices in the spectral axis that
                    # are masked in all pixels become masked in the spectral subset:
                    subset_mask = np.all(subset_mask, axis=spatial_axes)
            spectrum.mask |= subset_mask
        else:
            if subset_mask.ndim < spectrum.flux.ndim:
                # correct the shape of spectral/spatial axes when they're different:
                subset_mask = np.broadcast_to(subset_mask, spectrum.flux.shape)

            elif (subset_mask.ndim == spectrum.flux.ndim and
                  subset_mask.shape != spectrum.flux.shape):
                # if the number of dimensions is correct but shape is
                # different, rearrange the arrays for specutils:
                subset_mask = np.swapaxes(subset_mask, 1, 0)

            spectrum.mask = subset_mask
        return spectrum
