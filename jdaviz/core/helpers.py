"""
Helper classes are meant to provide a convenient user API for specific
configurations. They allow a separation of "viztool-specific" API and the glue
application objects.

See also https://github.com/spacetelescope/jdaviz/issues/104 for more details
on the motivation behind this concept.
"""

class ConfigHelper():
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
        from ..app import Application  # inside to prevent possible circular imports

        if app is None:
            self.app = Application(configuration=self._default_configuration)
        else:
            self.app = app
