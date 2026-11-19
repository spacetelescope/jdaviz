from functools import cached_property
from traitlets import Unicode
from jdaviz.core.template_mixin import WithCache, ValidatorMixin, LoaderBannerMessagesMixin

__all__ = ['BaseParser']


class BaseParser(WithCache, ValidatorMixin, LoaderBannerMessagesMixin):
    # rendered by the resolver (via parser_widgets) so that any _loader_message
    # calls from the parser are displayed in the loader UI
    template = Unicode("""
        <template>
            <j-loader-banner-messages :items="loader_message_items"></j-loader-banner-messages>
        </template>
        """).tag(sync=True)

    def __init__(self, app, inp):
        super().__init__()
        self._app = app
        self._input = inp

    @property
    def app(self):
        return self._app

    def _check_is_valid(self):
        """
        Checks if the input is valid (override in subclasses).

        The output of this method is wrapped by the IsValidWrapper
        helper class that converts the string to an inverted boolean,
        i.e. empty string => True, non-empty string => False
        since the string (when filled) carries error information.
        Furthermore, the actual 'is_valid' check is handled by the ValidatorMixin
        that wraps the check in a try/except statement so that individual
        '_check_is_valid' calls no longer need to catch potential failures.
        """
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
