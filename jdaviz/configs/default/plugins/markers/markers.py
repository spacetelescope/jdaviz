from traitlets import observe

from glue_jupyter.bqplot.image import BqplotImageView

from jdaviz.configs.imviz.helper import layer_is_image_data
from jdaviz.configs.cubeviz.helper import layer_is_cube_image_data
from jdaviz.core.marks import MarkersMark
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, ViewerSelectMixin, TableMixin
from jdaviz.core.user_api import PluginUserApi

__all__ = ['Markers']


@tray_registry('g-markers', label="Markers")
class Markers(PluginTemplateMixin, ViewerSelectMixin, TableMixin):
    """
    See the :ref:`Markers Plugin Documentation <imviz-markers>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    """
    template_file = __file__, "markers.vue"

    @property
    def user_api(self):
        return PluginUserApi(self, expose=('clear_table', 'export_table',))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        headers = ['x', 'y']

        if self.config in ['imviz', 'cubeviz', 'mosviz']:
            # image viewers
            headers += ['RA (ICRS)', 'DEC (ICRS)',
                        'RA (deg)', 'DEC (deg)',
                        'Value', 'viewer']
        if self.config in ['specviz', 'specviz2d', 'mosviz']:
            # 1d spectrum viewers
            headers += ['Spectral Axis', 'Pixel', 'Flux']
        if self.config in ['specviz2d', 'mosviz']:
            # 2d spectrum viewers
            headers += []

        headers += ['data_label']

        self.table.headers_avail = headers
        self.table.headers_visible = headers

    def _get_mark(self, viewer):
        matches = [mark for mark in viewer.figure.marks if isinstance(mark, MarkersMark)]
        if len(matches):
            return matches[0]
        mark = MarkersMark(viewer)
        viewer.figure.marks = viewer.figure.marks + [mark]
        return mark

    @property
    def marks(self):
        return {viewer_id: self._get_mark(viewer)
                for viewer_id, viewer in self.app._viewer_store.items()}

    @observe('plugin_opened')
    def _on_plugin_opened_changed(self, *args):
        if self.disabled_msg:
            return

        # toggle visibility of markers
        for mark in self.marks.values():
            mark.visible = self.plugin_opened

        # subscribe/unsubscribe to keypress events across all viewers
        for viewer in self.app._viewer_store.values():
            callback = self._viewer_callback(viewer, self._on_viewer_key_event)

            if self.plugin_opened:
                viewer.add_event_callback(callback, events=['keydown'])
            else:
                viewer.remove_event_callback(callback)

    def _on_viewer_key_event(self, viewer, data):
        if data['event'] == 'keydown' and data['key'] in ('m', 'M'):
            # TODO: refactor to share code with mouseover display if PR#1976 merged
            # TODO: merge with mouseover display entirely and show mouseover info in table

            row_info = self.app.session.application._tools['g-coords-info'].as_dict()

            if 'viewer' in self.table.headers_avail:
                row_info['viewer'] = viewer.reference_id

            self.table.add_item(row_info)

            self._get_mark(viewer).append_xy(row_info['x'], row_info['y'])

    def clear_table(self):
        """
        Clear all entries/markers from the current table.
        """
        super().clear_table()
        for mark in self.marks.values():
            mark.clear()
