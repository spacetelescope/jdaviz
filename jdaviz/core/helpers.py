"""
Helper classes are meant to provide a convenient user API for specific
configurations. They allow a separation of "viztool-specific" API and the glue
application objects.

See also https://github.com/spacetelescope/jdaviz/issues/104 for more details
on the motivation behind this concept.
"""
import re
import warnings

import numpy as np
import astropy.units as u
from glue.core import HubListener
from glue.core.message import SubsetCreateMessage

from jdaviz.app import Application

from IPython.display import display

from sidecar import Sidecar

__all__ = ['ConfigHelper']


class ConfigHelper(HubListener):
    """The Base Helper Class.
    Provides shared abstracted helper methods to the user.

    Subclasses should set ``_default_configuration`` if they are meant to be
    used with a specific configuration.

    Parameters
    ----------
    app : `~jdaviz.app.Application` or `None`
        The application object, or if `None`, creates a new one based on the
        default configuration for this helper.
    verbosity : {'debug', 'info', 'warning', 'error'}
        Verbosity of the popup messages in the application.
    history_verbosity : {'debug', 'info', 'warning', 'error'}
        Verbosity of the history logger in the application.
    """
    _default_configuration = 'default'

    def __init__(self, app=None, verbosity='warning', history_verbosity='info'):
        if app is None:
            self.app = Application(configuration=self._default_configuration)
        else:
            self.app = app
        self.app.verbosity = verbosity
        self.app.history_verbosity = history_verbosity

        # give a reference from the app back to this config helper.  These can be accessed from a
        # viewer via viewer.jdaviz_app and viewer.jdaviz_helper
        self.app._jdaviz_helper = self

        self.app.hub.subscribe(self, SubsetCreateMessage,
                               handler=lambda msg: self._propagate_callback_to_viewers('_on_subset_create', msg)) # noqa

    def _propagate_callback_to_viewers(self, method, msg):
        # viewers don't have access to the app/hub to subscribe to messages, so we'll
        # catch all messages here and pass them on to each of the viewers that
        # have the applicable method implemented.
        for viewer in self.app._viewer_store.values():
            if hasattr(viewer, method):
                getattr(viewer, method)(msg)

    def load_data(self, data, parser_reference=None, **kwargs):
        self.app.load_data(data, parser_reference=parser_reference, **kwargs)

    @property
    def fitted_models(self):
        """
        Returns the fitted model parameters.

        Returns
        -------
        parameters : dict
            dict of Quantity arrays, or None.
        """

        return self.app.fitted_models

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

    def get_model_parameters(self, models=None, model_label=None, x=None, y=None):
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

        param_dict = {}
        parameters_cube = {}
        param_x_y = {}
        param_units = {}

        for label in models:
            # 3d models take the form of "Model (1,2)" so this if statement
            # looks for that style and separates out the pertinent information.
            if " (" in label:
                label_split = label.split(" (")
                model_name = label_split[0] + "_3d"
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
                x_size = len(param_x_y[model_name]['x'])
                y_size = len(param_x_y[model_name]['y'])

                parameters_cube[model_name] = {x: np.zeros(shape=(x_size, y_size))
                                               for x in param_dict[model_name]}
            else:
                parameters_cube[model_name] = {x: 0
                                               for x in param_dict[model_name]}

        # This loop handles the actual placement of param.values and
        # param.units into the parameter_cubes dictionary.
        for label in models:
            if " (" in label:
                label_split = label.split(" (")
                model_name = label_split[0] + "_3d"

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

    def show(self, loc="inline", title=None):
        """Display the Jdaviz application.

        Parameters
        ----------
        loc : str
            The display location determines where to present the viz app.
            Supported locations:

            "inline": Display the Jdaviz application inline in a notebook.
            Note this is functionally equivalent to displaying the cell
            ``viz.app`` in the notebook.

            "sidecar": Display the Jdaviz application in a separate JupyterLab window from the
            notebook, the location of which is decided by the 'anchor.' right is the default

                Other anchors:

                * ``sidecar:right`` (The default, opens a tab to the right of display)
                * ``sidecar:tab-before`` (Full-width tab before the current notebook)
                * ``sidecar:tab-after`` (Full-width tab after the current notebook)
                * ``sidecar:split-right`` (Split-tab in the same window right of the notebook)
                * ``sidecar:split-left`` (Split-tab in the same window left of the notebook)
                * ``sidecar:split-top`` (Split-tab in the same window above the notebook)
                * ``sidecar:split-bottom`` (Split-tab in the same window below the notebook)

                See `jupyterlab-sidecar <https://github.com/jupyter-widgets/jupyterlab-sidecar>`_
                for the most up-to-date options.

        title : str, optional
            The title of the sidecar tab.  Defaults to the name of the
            application; e.g., "specviz".

            NOTE: Only applicable to a "sidecar" display.

        Notes
        -----
        If "sidecar" is requested in the "classic" Jupyter notebook, the app will appear inline,
        as only JupyterLab has a mechanism to have multiple tabs.
        """
        try:
            if loc == "inline":
                display(self.app)

            elif loc.startswith('sidecar'):
                # Use default behavior if loc is exactly 'sidecar', else split anchor from the arg
                anchor = None if loc == 'sidecar' else loc.split(':')[1]

                # If title unset, default to the viz config
                title = self.app.config if title is None else title

                scar = Sidecar(anchor=anchor, title=title)
                with scar:
                    display(self.app)

            elif loc == "new browser tab":
                raise NotImplementedError

            elif loc == "popout":
                raise NotImplementedError

            else:
                raise ValueError(f"Unrecognized display location: {loc}")

        except Exception as e:
            raise RuntimeError('Error in displaying Jdaviz') from e

    def show_in_sidecar(self, anchor=None, title=None):
        """
        Preserved for backwards compatibility
        Shows Jdaviz in a sidecar with the default anchor: right
        """
        warnings.warn('show_in_sidecar has been replaced with show(loc="sidecar")',
                      DeprecationWarning)
        location = 'sidecar' if anchor is None else f"sidecar:{anchor}"
        return self.show(loc=location, title=title)

    def show_in_new_tab(self, title=None):
        """
        Preserved for backwards compatibility
        Shows Jdaviz in a sidecar in a new tab to the right
        """
        warnings.warn('show_in_new_tab has been replaced with show(loc="sidecar:tab-after")',
                      DeprecationWarning)
        return self.show(loc="sidecar:tab-after", title=title)
