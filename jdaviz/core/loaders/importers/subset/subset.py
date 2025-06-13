from regions import Regions
from specutils import SpectralRegion
from traitlets import Unicode, Bool
from glue.core.message import (SubsetCreateMessage,
                               SubsetDeleteMessage)


from jdaviz.core.events import SubsetRenameMessage
from jdaviz.core.loaders.importers import BaseImporterToPlugin
from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.template_mixin import AutoTextField


__all__ = ['SubsetImporter']


@loader_importer_registry('Subset')
class SubsetImporter(BaseImporterToPlugin):
    template_file = __file__, "subset.vue"

    subset_label_value = Unicode().tag(sync=True)
    subset_label_default = Unicode().tag(sync=True)
    subset_label_auto = Bool(True).tag(sync=True)
    subset_label_invalid_msg = Unicode().tag(sync=True)

    def __init__(self, app, resolver, input, **kwargs):
        super().__init__(app, resolver, input, **kwargs)
        self.subset_label_default = 'Subset 1'
        self.subset_label = AutoTextField(self, 'subset_label_value',
                                          'subset_label_default',
                                          'subset_label_auto',
                                          'subset_label_invalid_msg')

        for msg in (SubsetCreateMessage, SubsetDeleteMessage, SubsetRenameMessage):
            self.hub.subscribe(self, msg,
                               handler=lambda _: self._on_label_changed())

        self.observe(self._on_label_changed, 'subset_label_value')
        self._on_label_changed()

    @property
    def is_valid(self):
        return (isinstance(self.input, (Regions, SpectralRegion))
                and self.has_default_plugin)

    @property
    def default_plugin(self):
        return 'Subset Tools'

    def _on_label_changed(self, msg={}):
        if not len(self.subset_label_value.strip()):
            # strip will raise the same error for a label of all spaces
            self.subset_label_invalid_msg = 'subset_label must be provided'
            return

        # ensure the default label is unique for the data-collection
        nsubsets = len(self.app.data_collection.subset_groups)
        self.subset_label_default = f"Subset {nsubsets + 1}"

        if self.app._check_valid_subset_label(self.subset_label_value, raise_if_invalid=False):
            self.subset_label_invalid_msg = 'invalid subset_label'
            return

        self.subset_label_invalid_msg = ''

    def __call__(self, subset_label=None):
        self.app._jdaviz_helper.plugins['Subset Tools'].import_region(self.input,
                                                                      subset_label=self.subset_label_value)  # noqa
