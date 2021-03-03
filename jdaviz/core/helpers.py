"""
Helper classes are meant to provide a convenient user API for specific
configurations. They allow a separation of "viztool-specific" API and the glue
application objects.

See also https://github.com/spacetelescope/jdaviz/issues/104 for more details
on the motivation behind this concept.
"""
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
        all_models = {}
        if hasattr(self.app, '_fitted_1d_models'):
            all_models = {**all_models, **self.app._fitted_1d_models}
        if hasattr(self.app, '_fitted_3d_model'):
            all_models = {**all_models, **self.app._fitted_3d_model}

        return all_models

    def get_1d_models(self):
        """
        Returns the 1D fitted model parameters.

        Returns
        -------
        parameters : dict
            dict with key being the model name and value being the Quantity model, or None.
        """
        if hasattr(self.app, '_fitted_1d_models'):
            return self.app._fitted_1d_models
        else:
            return None


    def get_3d_models(self):
        """
        Returns the 3D fitted model parameters.

        Returns
        -------
        parameters : dict
            dict of Quantity 2D arrays, or None.
        """
        if hasattr(self.app, '_fitted_3d_model'):
            return self.app._fitted_3d_model
        else:
            return None
