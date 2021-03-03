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
        MAX_DIMENSIONS = 5
        all_models = {}

        for dim in range(1, MAX_DIMENSIONS):
            attrname = f'_fitted_{dim}d_models'
            model = getattr(self.app, attrname, None)
            if model:
                all_models.update(model)

        return all_models

    def get_models(self, ndim=1):
        """
        Returns the fitted model parameters of ndim dimension(s).

        Parameters
        ----------
        ndim : int
            int that determines the dimension of the models that are returned

        Returns
        -------
        parameters : dict
            dict with key being the model name and value being the Quantity model, or None.
        """
        attrname = f'_fitted_{ndim}d_models'
        return getattr(self.app, attrname, None)
