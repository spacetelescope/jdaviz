import ipywidgets as w
from traitlets import Dict

from jdaviz.core.registries import tool_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template

__all__ = ['FileImport']


@tool_registry('g-file-import')
class FileImport(TemplateMixin):
    chosen_file = Dict().tag(sync=True)
    template = load_template("file_import.vue", __file__).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._file_upload = w.FileUpload()
        self.components = {'g-file-import': self._file_upload}

        self._file_upload.observe(self.on_counter_changed, names=['_counter'])

    def on_counter_changed(self, event):
        print("called")

        for name, data in self._file_upload.value.items():
            path = "/Users/nearl/Desktop/" + name
            print(path)
#             with open(path, 'w') as f:
#                 f.write("Test")

#             img = w.Image(
#                 value=data['content'],
#                 format='png',
#                 width=300,
#                 height=400,
#             )
#             display(img)


