from traitlets import Any, Int
from solara import FileDrop
from ipywidgets import widget_serialization
import io
import reacton

from jdaviz.core.registries import loader_resolver_registry
from jdaviz.core.loaders.resolvers import BaseResolver
from jdaviz.core.user_api import LoaderUserApi


@loader_resolver_registry('upload')
class UploadResolver(BaseResolver):
    template_file = __file__, "upload.vue"

    progress = Int(100).tag(sync=True)
    file_drop_widget = Any().tag(sync=True, **widget_serialization)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._file_info = None

        self.file_drop_widget_el = FileDrop(label="Drop file here",
                                            on_total_progress=self._on_total_progress,
                                            on_file=self._on_file_updated,
                                            lazy=False)
        self.file_drop_widget, rc = reacton.render(self.file_drop_widget_el)

    @property
    def user_api(self):
        return LoaderUserApi(self, expose=[])

    @property
    def is_valid(self):
        return True

    def _on_total_progress(self, progress):
        self.progress = progress

    def _on_file_updated(self, file_info):
        self._file_info = file_info
        self._update_format_items()
        self.progress = 100

    def __call__(self, local_path=None, timeout=60):
        # this will return a bytes object of the file contents
        return io.BytesIO(self._file_info.get('data'))
