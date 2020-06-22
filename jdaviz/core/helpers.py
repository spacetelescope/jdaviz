class ConfigHelper():
    """The Base Helper Class
    Provides shared abstracted helper methods to the user
    """
    _default_configuration = None

    def __init__(self, app=None):
        from ..app import Application  # inside to prevent possible circular imports

        if app is None:
            self.app = Application(configuration=self._default_configuration)
        else:
            self.app = app
