from astropy.table import Table as astropyTable
from traitlets import Any, Int
from solara import FileDropMultiple
from ipywidgets import widget_serialization
import io
import os
import reacton

from jdaviz.core.registries import loader_resolver_registry
from jdaviz.core.loaders.resolvers import BaseResolver
from jdaviz.core.user_api import LoaderUserApi


@loader_resolver_registry('file drop')
class FileDropResolver(BaseResolver):
    template_file = __file__, "file_drop.vue"

    progress = Int(100).tag(sync=True)
    nfiles = Int(0).tag(sync=True)
    file_drop_widget = Any().tag(sync=True, **widget_serialization)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._file_info = None

        self.file_drop_widget_el = FileDropMultiple(label="Drop file here",
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

    @property
    def default_label(self):
        # Use the first file name as the default label, if available.
        # Otherwise, return None.
        if self._file_info and 'name' in self._file_info:
            return os.path.splitext(self._file_info['name'])[0]
        return None

    def _parsed_input_to_table(self, parsed_input):
        # support loading in from file drop resolver
        for format in ('csv', 'ascii', 'fits', 'votable'):
            try:
                parsed_input = astropyTable.read(parsed_input, format=format)
                return parsed_input
            except Exception:  # nosec
                pass
        return None

    def _on_total_progress(self, progress):
        self.progress = progress

    def _on_file_updated(self, file_infos):
        self.nfiles = len(file_infos)
        self._file_info = file_infos[0]
        self._resolver_input_updated()
        self._update_format_items()
        self.progress = 100

    def parse_input(self):
        # this will return a bytes object of the file contents
        return io.BytesIO(self._file_info.get('data'))
