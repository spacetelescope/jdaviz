import numpy as np
from traitlets import Bool, observe

from jdaviz.core.events import ViewerAddedMessage
from jdaviz.core.marks import MarkersMark
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, ViewerSelectMixin, TableMixin
from jdaviz.core.user_api import PluginUserApi

__all__ = ['Markers']


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
    uses_active_status = Bool(True).tag(sync=True)

    _default_table_values = {'spectral_axis': np.nan,
                             'spectral_axis:unit': '',
                             'slice': np.nan,
                             'pixel': (np.nan, np.nan),
                             'pixel:unreliable': None,
                             'world': (np.nan, np.nan),
                             'world:unreliable': None,
                             'value': np.nan,
                             'value:unit': '',
                             'value:unreliable': None,
                             'index': np.nan}

    @property
    def user_api(self):
        return PluginUserApi(self, expose=('clear_table', 'export_table',))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.config == 'cubeviz':
            headers = ['spectral_axis', 'spectral_axis:unit',
                       'slice', 'pixel',
                       'world', 'value', 'value:unit', 'viewer']

        elif self.config == 'imviz':
            headers = ['pixel', 'pixel:unreliable',
                       'world', 'world:unreliable',
                       'value', 'value:unit', 'value:unreliable',
                       'viewer']

        elif self.config == 'specviz':
            headers = ['spectral_axis', 'spectral_axis:unit',
                       'index', 'value', 'value:unit']
        elif self.config == 'specviz2d':
            # TODO: add "index" if/when specviz2d supports plotting spectral_axis
            headers = ['spectral_axis', 'spectral_axis:unit',
                       'pixel', 'value', 'value:unit', 'viewer']
        elif self.config == 'mosviz':
            headers = ['spectral_axis', 'spectral_axis:unit',
                       'pixel', 'world', 'index', 'value', 'value:unit',
                       'viewer']
        else:
            # allow downstream configs to override headers
            headers = kwargs.get('headers', [])

        headers += ['data_label']

        self.table.headers_avail = headers
        self.table.headers_visible = headers
        self.table._default_values_by_colname = self._default_table_values

        # subscribe to mouse events on any new viewers
        self.hub.subscribe(self, ViewerAddedMessage, handler=self._on_viewer_added)

    def _create_viewer_callbacks(self, viewer):
        if not self.is_active:
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

    @property
    def coords_info(self):
        return self.app.session.application._tools['g-coords-info']

    @observe('is_active')
    def _on_is_active_changed(self, *args):
        if self.disabled_msg:
            return

        # toggle visibility of markers
        for mark in self.marks.values():
            mark.visible = self.is_active

        # subscribe/unsubscribe to keypress events across all viewers
        for viewer in self.app._viewer_store.values():
            if not hasattr(viewer, 'figure'):
                # table viewer, etc
                continue
            callback = self._viewer_callback(viewer, self._on_viewer_key_event)

            if self.is_active:
                viewer.add_event_callback(callback, events=['keydown'])
            else:
                viewer.remove_event_callback(callback)

    def _on_viewer_key_event(self, viewer, data):
        if data['event'] == 'keydown' and data['key'] == 'm':
            row_info = self.coords_info.as_dict()

            if 'viewer' in self.table.headers_avail:
                row_info['viewer'] = viewer.reference if viewer.reference is not None else viewer.reference_id  # noqa

            for k in self.table.headers_avail:
                row_info.setdefault(k, self._default_table_values.get(k, ''))

            try:
                self.table.add_item({k: v for k, v in row_info.items()
                                     if k in self.table.headers_avail})
            except ValueError as err:
                raise ValueError(f'failed to add {row_info} to table: {repr(err)}')

            x, y = row_info['axes_x'], row_info['axes_y']
            self._get_mark(viewer).append_xy(getattr(x, 'value', x), getattr(y, 'value', y))

    def clear_table(self):
        """
        Clear all entries/markers from the current table.
        """
        super().clear_table()
        for mark in self.marks.values():
            mark.clear()
