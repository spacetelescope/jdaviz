from traitlets import List, Unicode, observe

from jdaviz.configs.default.plugins.viewers import ScatterViewer
from jdaviz.core.user_api import ViewerCreatorUserApi
from jdaviz.core.viewer_creators import BaseViewerCreator
from jdaviz.core.registries import viewer_creator_registry
from jdaviz.core.template_mixin import SelectPluginComponent
from jdaviz.utils import att_to_componentid


__all__ = ['ScatterViewerCreator']


@viewer_creator_registry('Scatter', overwrite=True)
class ScatterViewerCreator(BaseViewerCreator):
    template_file = __file__, "scatter.vue"

    xatt_items = List().tag(sync=True)
    xatt_selected = Unicode().tag(sync=True)

    yatt_items = List().tag(sync=True)
    yatt_selected = Unicode().tag(sync=True)

    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.viewer_label_default = 'Scatter'
        self.dataset.filters = ['not_ramp']

        self.xatt = SelectPluginComponent(self,
                                          items='xatt_items',
                                          selected='xatt_selected',
                                          default_mode='first')
        self.yatt = SelectPluginComponent(self,
                                          items='yatt_items',
                                          selected='yatt_selected',
                                          default_mode='second')

    @property
    def user_api(self):
        return ViewerCreatorUserApi(self, expose=('xatt', 'yatt'))

    @property
    def viewer_class(self):
        return ScatterViewer

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
        self.yatt._manual_options = valid_atts
        self.yatt._update_items()

    def __call__(self):
        nv = super().__call__()
        gv_state = nv._obj.glue_viewer.state
        if self.xatt.selected != '':
            gv_state.x_att = att_to_componentid(gv_state.x_att_helper, self.xatt.selected)
        if self.yatt.selected != '':
            gv_state.y_att = att_to_componentid(gv_state.y_att_helper, self.yatt.selected)
        if self.xatt.selected != '' or self.yatt.selected != '':
            nv._obj.glue_viewer.reset_limits()
        return nv
