from traitlets import Any
from solara import FileDrop
from ipywidgets import widget_serialization

from jdaviz.core.registries import loader_resolver_registry
from jdaviz.core.loaders.resolvers import BaseResolver
from jdaviz.core.user_api import LoaderUserApi


@loader_resolver_registry('upload')
class UploadResolver(BaseResolver):
    template_file = __file__, "upload.vue"

    file_drop_widget = Any().tag(sync=True, **widget_serialization)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._file_info = None
        self.file_drop_widget = FileDrop.widget(label="Drop file here",
                                                on_total_progress=self._on_total_progress,
                                                on_file=self._on_file_updated,
                                                lazy=False)

    @property
    def user_api(self):
        return LoaderUserApi(self, expose=[])

    @property
    def is_valid(self):
        return False

    def _on_total_progress(self, progress):
        print("*** UploadResolver._on_total_progress", progress)

    def _on_file_updated(self, file_info):
        print("*** UploadResolver._on_file_updated")
        self._file_info = file_info
        self._update_format_items()

    def __call__(self, local_path=None, timeout=60):
        return self._file_info.file_obj
