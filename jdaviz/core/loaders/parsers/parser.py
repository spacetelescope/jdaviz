from functools import cached_property


class BaseParser:
    def __init__(self, app, inp):
        self._app = app
        self._input = inp

    @property
    def app(self):
        return self._app

    @property
    def is_valid(self):
        raise NotImplementedError("Subclasses must implement is_valid property")

    @property
    def input(self):
        return self._input

    @cached_property
    def output(self):
        raise NotImplementedError("Subclasses must implement output property")

    def __call__(self):
        return self.output
