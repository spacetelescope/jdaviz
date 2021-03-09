"""
Helper classes are meant to provide a convenient user API for specific
configurations. They allow a separation of "viztool-specific" API and the glue
application objects.

See also https://github.com/spacetelescope/jdaviz/issues/104 for more details
on the motivation behind this concept.
"""
import re

from ..app import Application
from glue.core import HubListener

__all__ = ['ConfigHelper']


class ConfigHelper(HubListener):
    """The Base Helper Class
    Provides shared abstracted helper methods to the user.

    Subclasses should set `_default_configuration` if they are meant to be
    used with a specific configuration.

    Parameters
    ----------
    app : jdaviz.app.Application or None
        The application object, or if None, creates a new one based on the
        default configuration for this helper.
    """
    _default_configuration = 'default'

    def __init__(self, app=None):
        if app is None:
            self.app = Application(configuration=self._default_configuration)
        else:
            self.app = app

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

    def get_models(self, models=None, model_label="default", x=None, y=None):
        """
        Loop through all models and output models of the label model_label.
        If x or y is set, return model_labels of those (x, y) coordinates.
        If x and y are None, print all models regardless of coordinates.

        Parameters
        ----------
        models : dict
            A dict of models, with the key being the label name and the value
            being the model object. Defaults to `self.fitted_models` if no
            parameter is provided.
        model_label : str
            The name of the model that will be found and returned. If it
            equals default, every model present will be returned.
        x : int
            The x coordinate of the model spaxels that will be returned.
        y : int
            The y coordinate of the model spaxels that will be returned.

        Returns
        -------
        :dict: dict of the selected models.
        """
        selected_models = {}
        # If models is not provided, use the app's fitted models
        if not models:
            models = self.fitted_models

        # Loop through all keys in the dict models
        for label in models:
            # If no label was provided, use label name without coordinates.
            if model_label == "default" and " (" in label:
                find_label = label.split(" (")[0]
            # If coordinates are not present, just use the label.
            elif model_label == "default":
                find_label = label
            else:
                find_label = model_label

            # If x and y is set, return keys that match the model plus that
            # coordinate pair. If only x or y is set, return keys that fit
            # that value for the appropriate coordinate. If neither is set,
            # add the model object to the selected_models dict with the label
            # as the key.
            if x and y:
                find_label = f"{find_label} ({x}, {y})"
            elif x:
                find_label = r"{} \({}, .+\)".format(find_label, x)
            elif y:
                find_label = f"{find_label} (.+, {y})"
            else:
                selected_models[label] = models[label]

            if re.search(find_label, label):
                selected_models[label] = models[label]

        return selected_models
