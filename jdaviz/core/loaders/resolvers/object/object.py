from pathlib import Path

from traitlets import Unicode

from jdaviz.core.registries import loader_resolver_registry
from jdaviz.core.loaders.resolvers import BaseResolver
from jdaviz.core.user_api import LoaderUserApi


__all__ = ['ObjectResolver', 'PresetObjectResolver']


@loader_resolver_registry('object')
class ObjectResolver(BaseResolver):
    template_file = __file__, "object.vue"
    default_input = 'object'
    requires_api_support = True

    title = Unicode("Python Object (from API)").tag(sync=True)
    object_repr = Unicode("").tag(sync=True)

    def __init__(self, *args, **kwargs):
        self._object = None
        super().__init__(*args, **kwargs)

    @property
    def user_api(self):
        return LoaderUserApi(self, expose=['object'])

    @property
    def is_valid(self):
        if isinstance(self.object, str):
            # reject strings that should go through file
            # or url resolvers instead
            if Path(self.object).exists():
                return False
            if self.object.strip().startswith(('http://', 'https://',
                                               'ftp://', 's3://', 'mast://')):
                return False
        return not isinstance(self.object, Path)

    @property
    def object(self):
        return self._object

    @object.setter
    def object(self, obj):
        self._object = obj
        self.object_repr = f"<{obj.__class__.__name__} object>"
        self._resolver_input_updated()

    def parse_input(self):
        return self.object


class PresetObjectResolver(ObjectResolver):
    """
    An ObjectResolver variant with a pre-set object that doesn't show
    input widgets. Used for programmatically adding objects.

    This resolver behaves like the object resolver but hides the input fields
    by setting hide_resolver_inputs=True, while still showing query results
    and importer selection.
    """

    def __init__(self, object, title=None, *args, **kwargs):
        # Store object and title before calling parent's init
        _preset_object = object
        _preset_title = title

        # Call parent (ObjectResolver) init
        super().__init__(*args, **kwargs)

        # Set the object after initialization
        self.object = _preset_object

        # Set custom title if provided
        if _preset_title is not None:
            self.title = _preset_title

        # Override to hide input fields
        self.hide_resolver_inputs = True
