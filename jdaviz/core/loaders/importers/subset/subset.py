from regions import Regions
from specutils import SpectralRegion
from traitlets import Unicode, Bool, observe
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

        # set the default label to be the same as glue would set if
        # not passing subset_label explicitly
        self.subset_label_default = f"Subset {self.app.data_collection._sg_count + 1}"

        if self.subset_label_value == self.subset_label_default:
            # _check_valid_subset_label will say this is invalid,
            # once that changes, this block can be removed.
            self.subset_label_invalid_msg = ''
            return

        try:
            self.app._check_valid_subset_label(self.subset_label_value, raise_if_invalid=True)
        except ValueError as e:
            self.subset_label_invalid_msg = f'invalid subset_label: {str(e)}'
            return

        self.subset_label_invalid_msg = ''

    @observe('subset_label_invalid_msg')
    def _set_import_disabled(self, change={}):
        self.resolver.import_disabled = len(self.subset_label_invalid_msg) > 0

    def __call__(self, show_in_viewer=True):
        if self.subset_label_invalid_msg:
            raise ValueError(self.subset_label_invalid_msg)
        if self.subset_label_value.strip() == self.subset_label_default:
            # no need to pass subset_label since it is Subset N,
            # and otherwise the backend will raise an error
            kwargs = {}
        else:
            kwargs = {'subset_label': self.subset_label_value.strip()}
        self.app._jdaviz_helper.plugins['Subset Tools'].import_region(self.input,
                                                                      **kwargs)  # noqa
