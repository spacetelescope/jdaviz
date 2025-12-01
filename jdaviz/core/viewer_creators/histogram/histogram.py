from traitlets import List, Unicode, observe

from jdaviz.configs.default.plugins.viewers import HistogramViewer
from jdaviz.core.user_api import ViewerCreatorUserApi
from jdaviz.core.viewer_creators import BaseViewerCreator
from jdaviz.core.registries import viewer_creator_registry
from jdaviz.core.template_mixin import SelectPluginComponent
from jdaviz.utils import att_to_componentid


__all__ = ['HistogramViewerCreator']


@viewer_creator_registry('Histogram', overwrite=True)
class HistogramViewerCreator(BaseViewerCreator):
    template_file = __file__, "histogram.vue"
    xatt_items = List().tag(sync=True)
    xatt_selected = Unicode().tag(sync=True)

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.viewer_label_default = 'Histogram'
        self.dataset.filters = ['not_ramp']

        self.xatt = SelectPluginComponent(self,
                                          items='xatt_items',
                                          selected='xatt_selected',
                                          default_mode='first')

    @property
    def user_api(self):
        return ViewerCreatorUserApi(self, expose=('xatt',))

    @property
    def viewer_class(self):
        return HistogramViewer

    @observe('dataset_selected')
    def _on_dataset_selected_change(self, event):
        if not hasattr(self, 'dataset') or not hasattr(self, 'xatt'):
            return
        dc_items = self.dataset.selected_dc_item
        if not self.dataset.is_multiselect:
            dc_items = [dc_items] if dc_items else []
        valid_atts = []
        for dc_item in dc_items:
            valid_atts += [c.label for c in dc_item.components
                           if 'Pixel Axis' not in c.label]
        valid_atts = sorted(set(valid_atts))
        self.xatt._manual_options = valid_atts
        self.xatt._update_items()

    def __call__(self):
        nv = super().__call__()
        gv_state = nv._obj.glue_viewer.state
        if self.xatt.selected != '':
            gv_state.x_att = att_to_componentid(gv_state.x_att_helper, self.xatt.selected)
        if len(nv._obj.glue_viewer.layers):
            nv._obj.glue_viewer.reset_limits()
        return nv
