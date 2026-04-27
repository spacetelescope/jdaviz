from functools import cached_property
from jdaviz.core.template_mixin import WithCache, ValidatorMixin

__all__ = ['BaseParser']


class BaseParser(WithCache, ValidatorMixin):
    def __init__(self, app, inp):
        self._app = app
        self._input = inp

    @property
    def app(self):
        return self._app

    def _check_is_valid(self):
        raise NotImplementedError("Subclasses must implement _check_is_valid()")  # pragma: nocover

    @property
    def input(self):
        return self._input

    @cached_property
    def output(self):
        raise NotImplementedError("Subclasses must implement output property")  # pragma: nocover

    def _cleanup(self):
        """Cleanup any resources held by the parser."""
        return
