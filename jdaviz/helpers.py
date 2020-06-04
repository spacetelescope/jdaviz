from .app import Application

class ConfigHelper():
    """The Base Helper Class
    Provides shared abstracted helper methods to the user
    """
    def __init__(self, configuration=None):
        self._app = Application(configuration=configuration)
