import numpy as np
from traitlets import observe

from jdaviz.core.events import ViewerAddedMessage
from jdaviz.core.marks import MarkersMark
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, ViewerSelectMixin, TableMixin
from jdaviz.core.user_api import PluginUserApi

__all__ = ['Markers']

_default_table_values = {'x': np.nan,
                         'x:unit': '',
                         'y': np.nan,
                         'y:unit': '',
                         'xy:unreliable': False,
                         'slice index': np.nan,
                         'slice wavelength': np.nan,
                         'slice wavelength:unit': '',
                         'value': np.nan,
                         'value:unit': '',
                         'RA (ICRS)': '',
                         'DEC (ICRS)': '',
                         'RA (deg)': np.nan,
                         'DEC (deg)': np.nan,
                         'radec:unreliable': False,
                         'index': np.nan}


@tray_registry('g-markers', label="Markers")
class Markers(PluginTemplateMixin, ViewerSelectMixin, TableMixin):
    """
    See the :ref:`Markers Plugin Documentation <markers-plugin>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * :meth:`clear_table`
    * :meth:`~jdaviz.core.template_mixin.TableMixin.export_table`
    """
    template_file = __file__, "markers.vue"

    @property
    def user_api(self):
        return PluginUserApi(self, expose=('clear_table', 'export_table',))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        headers = ['x', 'x:unit', 'y', 'y:unit']

        if self.config == 'cubeviz':
            headers += ['slice index', 'slice wavelength', 'slice wavelength:unit']

        if self.config in ('imviz', 'cubeviz', 'mosviz'):
            # image viewers
            headers += ['xy:unreliable',
                        'RA (ICRS)', 'DEC (ICRS)',
                        'RA (deg)', 'DEC (deg)',
                        'radec:unreliable',
                        'value', 'value:unit',
                        'viewer']
        if self.config in ('specviz', 'specviz2d', 'mosviz'):
            # 1d spectrum viewers
            headers += ['index']
        # NOTE: Uncomment when there is something to add.
        # if self.config in ('specviz2d', 'mosviz'):
        #     # 2d spectrum viewers
        #     headers += []

        headers += ['data_label']

        self.table.headers_avail = headers
        self.table.headers_visible = headers

        # subscribe to mouse events on any new viewers
        self.hub.subscribe(self, ViewerAddedMessage, handler=self._on_viewer_added)

    def _create_viewer_callbacks(self, viewer):
        if not self.plugin_opened:
            return

        callback = self._viewer_callback(viewer, self._on_viewer_key_event)
        viewer.add_event_callback(callback, events=['keydown'])

    def _on_viewer_added(self, msg):
        self._create_viewer_callbacks(self.app.get_viewer_by_id(msg.viewer_id))

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
                for viewer_id, viewer in self.app._viewer_store.items()
                if hasattr(viewer, 'figure')}

    @observe('plugin_opened')
    def _on_plugin_opened_changed(self, *args):
        if self.disabled_msg:
            return

        # toggle visibility of markers
        for mark in self.marks.values():
            mark.visible = self.plugin_opened

        # subscribe/unsubscribe to keypress events across all viewers
        for viewer in self.app._viewer_store.values():
            if not hasattr(viewer, 'figure'):
                # table viewer, etc
                continue
            callback = self._viewer_callback(viewer, self._on_viewer_key_event)

            if self.plugin_opened:
                viewer.add_event_callback(callback, events=['keydown'])
            else:
                viewer.remove_event_callback(callback)

    def _on_viewer_key_event(self, viewer, data):
        if data['event'] == 'keydown' and data['key'] == 'm':
            row_info = self.app.session.application._tools['g-coords-info'].as_dict()

            if 'viewer' in self.table.headers_avail:
                row_info['viewer'] = viewer.reference if viewer.reference is not None else viewer.reference_id  # noqa

            for k in self.table.headers_avail:
                row_info.setdefault(k, _default_table_values.get(k, ''))

            try:
                self.table.add_item(row_info)
            except ValueError as err:
                raise ValueError(f'failed to add {row_info} to table: {repr(err)}')

            x, y = row_info['x'], row_info['y']
            # TODO: will need to test/update when adding support for display units
            self._get_mark(viewer).append_xy(getattr(x, 'value', x), getattr(y, 'value', y))

    def clear_table(self):
        """
        Clear all entries/markers from the current table.
        """
        super().clear_table()
        for mark in self.marks.values():
            mark.clear()
