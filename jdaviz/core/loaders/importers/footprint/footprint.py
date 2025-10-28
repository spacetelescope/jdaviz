import regions
import numpy as np
from traitlets import Unicode, Bool, observe


from jdaviz.core.loaders.importers import BaseImporterToPlugin
from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.template_mixin import AutoTextField
from jdaviz.core.user_api import ImporterUserApi


__all__ = ['FootprintImporter']


@loader_importer_registry('Footprint')
class FootprintImporter(BaseImporterToPlugin):
    template_file = __file__, "footprint.vue"

    footprint_label_value = Unicode().tag(sync=True)
    footprint_label_default = Unicode().tag(sync=True)
    footprint_label_auto = Bool(True).tag(sync=True)
    footprint_label_invalid_msg = Unicode().tag(sync=True)

    def __init__(self, app, resolver, parser, input, **kwargs):
        super().__init__(app, resolver, parser, input, **kwargs)
        self.footprint_label_default = 'default'
        self.footprint_label = AutoTextField(self, 'footprint_label_value',
                                             'footprint_label_default',
                                             'footprint_label_auto',
                                             'footprint_label_invalid_msg')

        self.observe(self._on_label_changed, 'footprint_label_value')
        self._on_label_changed()

    @property
    def is_valid(self):
        # TODO: handle str > region in parser

        def _ensure_sky(region):
            if isinstance(region, regions.Regions):
                return np.all([_ensure_sky(reg) for reg in region.regions])
            return hasattr(region, 'to_pixel')

        return (isinstance(self.input, (regions.Region, regions.Regions))
                and _ensure_sky(self.input)
                and self.has_default_plugin)

    @property
    def user_api(self):
        return ImporterUserApi(self, expose=['footprint_label'])

    @property
    def default_plugin(self):
        return 'Footprints'

    def _on_label_changed(self, msg={}):
        if not len(self.footprint_label_value.strip()):
            # strip will raise the same error for a label of all spaces
            self.footprint_label_invalid_msg = 'footprint_label must be provided'
            return

        if self.footprint_label_value == self.footprint_label_default:
            # _check_valid_footprint_label will say this is invalid,
            # once that changes, this block can be removed.
            self.footprint_label_invalid_msg = ''
            return

        self.footprint_label_invalid_msg = ''

    @observe('footprint_label_invalid_msg')
    def _set_import_disabled(self, change={}):
        self.import_disabled = len(self.footprint_label_invalid_msg) > 0

    def __call__(self):
        if self.footprint_label_invalid_msg:
            raise ValueError(self.footprint_label_invalid_msg)

        plg = self.app._jdaviz_helper.plugins['Footprints']
        if self.footprint_label_value not in plg.overlay.choices:
            # TODO: show warning in UI when entry already exists
            plg.add_overlay(self.footprint_label_value)
        plg.import_region(self.input)
