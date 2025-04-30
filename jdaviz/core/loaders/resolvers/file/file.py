import os
from traitlets import Any, Unicode, observe
from ipywidgets import widget_serialization
from solara import FileBrowser
import reacton

from jdaviz.core.registries import loader_resolver_registry
from jdaviz.core.loaders.resolvers import BaseResolver
from jdaviz.core.user_api import LoaderUserApi


__all__ = ['FileResolver']


@loader_resolver_registry('file')
class FileResolver(BaseResolver):
    template_file = __file__, "file.vue"
    default_input = 'filepath'

    file_chooser_widget = Any().tag(sync=True, **widget_serialization)
    filepath = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        start_path = os.environ.get('JDAVIZ_START_DIR', os.path.curdir)

        self.file_chooser_widget_el = FileBrowser(directory=start_path,
                                                  on_path_select=self._on_file_chooser_path_changed,
                                                  can_select=True)
        self.file_chooser_widget, rc = reacton.render(self.file_chooser_widget_el)
        super().__init__(*args, **kwargs)

    @property
    def user_api(self):
        return LoaderUserApi(self, expose=['filepath'])

    def _on_file_chooser_path_changed(self, path):
        self.filepath = str(path)

    @observe('filepath')
    def _on_filepath_changed(self, change):
        # when the filepath traitlet is changed, need to update the file_chooser_widget to match the corresponding path
#        if self._file_upload.file_path != change['new']:
#            path, file = os.path.split(change['new'])
#            if path == '':
#                path = './'
#            self._file_upload._set_form_values(path, file)
        self._update_format_items()

    @property
    def is_valid(self):
        return os.path.exists(self.filepath) and os.path.isfile(self.filepath)  # noqa

    def __call__(self):
        return self.filepath
