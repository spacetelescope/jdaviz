import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
import traitlets
import ipywidgets as widgets

from jdaviz.core.events import (ViewerAddedMessage, ChangeRefDataMessage,
                                AddDataMessage, RemoveDataMessage,
                                MarkersPluginUpdate)
from jdaviz.core.marks import MarkersMark, DistanceMeasurement
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, ViewerSelectMixin, TableMixin, Table
from jdaviz.core.user_api import PluginUserApi

__all__ = ['Markers']


@tray_registry('g-markers', label="Markers",
               category='core', sidebar='info', subtab=1)
class Markers(PluginTemplateMixin, ViewerSelectMixin, TableMixin):
    """
    See the :ref:`Markers Plugin Documentation <markers-plugin>` for more details.
    
    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:
    
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.close_in_tray`
    * :meth:`~jdaviz.core.template_mixin.TableMixin.clear_table`
    * :meth:`~jdaviz.core.template_mixin.TableMixin.export_table`
    """
    distance_display = traitlets.Unicode("N/A").tag(sync=True)
    template_file = __file__, "markers.vue"
    uses_active_status = traitlets.Bool(True).tag(sync=True)
    
    distances_table = traitlets.Instance(Table).tag(sync=True, **widgets.widget_serialization)

    _default_table_values = {'spectral_axis': np.nan,
                             'spectral_axis:unit': '',
                             'slice': np.nan,
                             'pixel_x': np.nan,
                             'pixel_y': np.nan,
                             'pixel:unreliable': None,
                             'world_ra': np.nan,
                             'world_dec': np.nan,
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
            headers = ['spectral_axis', 'spectral_axis:unit', 'slice',
                       'pixel_x', 'pixel_y', 'world_ra', 'world_dec',
                       'value', 'value:unit', 'viewer']
        
        elif self.config == 'imviz':
            headers = ['pixel_x', 'pixel_y', 'pixel:unreliable',
                       'world_ra', 'world_dec', 'world:unreliable',
                       'value', 'value:unit', 'value:unreliable',
                       'viewer']
        
        elif self.config == 'specviz':
            headers = ['spectral_axis', 'spectral_axis:unit',
                       'index', 'value', 'value:unit']
        
        elif self.config in ('specviz2d', 'deconfigged'):
            # TODO: add "index" if/when specviz2d supports plotting spectral_axis
            headers = ['spectral_axis', 'spectral_axis:unit',
                       'pixel_x', 'pixel_y', 'value', 'value:unit', 'viewer']
        
        elif self.config == 'mosviz':
            headers = ['spectral_axis', 'spectral_axis:unit',
                       'pixel_x', 'pixel_y', 'world_ra', 'world_dec', 'index',
                       'value', 'value:unit', 'viewer']
        else:
            # allow downstream configs to override headers
            headers = kwargs.get('headers', [])
            
        headers += ['data_label']
        
        self.table.headers_avail = headers
        self.table.headers_visible = headers
        self.table._default_values_by_colname = self._default_table_values
        
        self._distance_marks = {}
        self._distance_first_point = None
        self._distance_line_endpoints = None
        
        self.distance_display = "N/A"

        def clear_table_callback():
            for mark in self.marks.values():
                mark.clear()
                
            for viewer_id, dist_measure in self._distance_marks.items():
                viewer = self.app.get_viewer_by_id(viewer_id)
                viewer.figure.marks = [m for m in viewer.figure.marks if m not in dist_measure.marks]
            self._distance_marks.clear()
            self.distance_display = "N/A"
            
            self._distance_first_point = None
            self._distance_line_endpoints = None
            if self.distances_table is not None:
                self.distances_table.clear_table()
            self.hub.broadcast(MarkersPluginUpdate(table_length=0, sender=self))
            
        self.table._clear_callback = clear_table_callback
        
        # subscribe to mouse events on any new viewers
        self.hub.subscribe(self, ViewerAddedMessage, handler=self._on_viewer_added)
        
        # account for image rotation due to a change in reference data
        self.hub.subscribe(self, ChangeRefDataMessage,
                           handler=lambda msg: self._recompute_mark_positions(msg.viewer))
                           
        # enable/disable mark based on whether parent data entry is in viewer
        self.hub.subscribe(self, AddDataMessage,
                           handler=lambda msg: self._recompute_mark_positions(msg.viewer))
                           
        self.hub.subscribe(self, RemoveDataMessage,
                           handler=lambda msg: self._recompute_mark_positions(msg.viewer))
        
        self.docs_description = """Press 'm' with the cursor over a viewer to log\
                                the mouseover information. To change the\
                                selected layer, click the layer cycler in the\
                                mouseover information section of the app-level\
                                toolbar.
        
Press 'd' twice to measure the distance between any two points. Hold the 'Option' (Mac) or 'Alt' key while pressing 'd' to snap measurement points to the nearest marker.
        """
                                 
        # description displayed under plugin title in tray
        self._plugin_description = 'Create markers on viewers.'

    @traitlets.default('distances_table')
    def _default_distances_table(self):
        table = Table(
            self,
            title='Measurements',
            headers=['Start RA', 'Start Dec', 'End RA', 'End Dec',
                     'Separation (arcsec)', 'Distance (pix)', 'Position Angle (deg)'],
        )
        return table

    def _create_viewer_callbacks(self, viewer):
        if not self.is_active:
            return
        
        callback = self._viewer_callback(viewer, self._on_viewer_key_event)
        viewer.add_event_callback(callback, events=['keydown'])
    
    def _on_viewer_added(self, msg):
        self._create_viewer_callbacks(self.app.get_viewer_by_id(msg.viewer_id))
    
    def _recompute_mark_positions(self, viewer):
        if self.table is None or len(self.table.items) == 0:
            return
        if 'world_ra' not in self.table.headers_avail:
            return

        qtable = self.table.export_table()
        if qtable is None:
            return
            
        viewer_id = viewer.reference if viewer.reference is not None else viewer.reference_id
        viewer_loaded_data = [lyr.layer.label for lyr in viewer.layers]
        data_labels = qtable['data_label']
        viewer_labels = qtable['viewer']
        # note: could eventually have a user-provided switch to show markers in other viewers
        # by just skipping this first viewer_label == viewer_id check
        in_viewer = [viewer_label == viewer_id and data_label in viewer_loaded_data
                     for viewer_label, data_label in zip(viewer_labels, data_labels)]
                     
        viewer_mark = self._get_mark(viewer)
        if not np.any(in_viewer):
            viewer_mark.x, viewer_mark.y = [], []
            return
            
        orig_world_x = np.asarray(qtable['world_ra'][in_viewer])
        orig_world_y = np.asarray(qtable['world_dec'][in_viewer])
        pixel_unreliable = np.asarray(qtable['pixel:unreliable'][in_viewer])
        
        if self.app._align_by.lower() == 'wcs':
            # convert from the sky coordinates in the table to pixels via the WCS of the current
            # reference data
            new_wcs = viewer.state.reference_data.coords
            try:
                new_x, new_y = new_wcs.world_to_pixel_values(orig_world_x*u.deg,
                                                             orig_world_y*u.deg)
                for coord in [new_x, new_y]:
                    coord[pixel_unreliable] = np.nan
                    
            except Exception:
                # fail gracefully
                new_x, new_y = [], []
        elif self.app._align_by == 'pixels':
            # we need to convert based on the WCS of the individual data layers on which each mark
            # was first created
            new_x, new_y = np.zeros_like(orig_world_x), np.zeros_like(orig_world_y)
            in_viewer_qtable = qtable[in_viewer]
            for data_label in np.unique(in_viewer_qtable['data_label']):
                these = in_viewer_qtable['data_label'] == data_label
                if not np.any(these):
                    continue
                
                wcs = self.app.data_collection[data_label].coords
                try:
                    original_indices_mask = (qtable['data_label'] == data_label) & in_viewer
                    new_x[original_indices_mask], new_y[original_indices_mask] = wcs.world_to_pixel_values(
                        np.asarray(qtable['world_ra'][original_indices_mask]) * u.deg,
                        np.asarray(qtable['world_dec'][original_indices_mask]) * u.deg
                    )
                except Exception:
                    # fail gracefully
                    new_x, new_y = [], []
                    break
        else:
            raise NotImplementedError(f"align_by {self.app._align_by} not implemented")
            
        viewer_mark.x, viewer_mark.y = new_x, new_y

        if viewer_id in self._distance_marks and self._distance_line_endpoints is not None:
            dist_measure = self._distance_marks[viewer_id]
            p1 = self._distance_line_endpoints['p1']
            p2 = self._distance_line_endpoints['p2']

            world_avail = ('world_ra' in p1 and 'world_ra' in p2 and
                           p1.get('world_ra') is not None and p2.get('world_ra') is not None)

            if not world_avail:
                dist_measure.visible = False
                return

            try:
                c1 = SkyCoord(p1['world_ra'], p1['world_dec'], unit='deg', frame='icrs')
                c2 = SkyCoord(p2['world_ra'], p2['world_dec'], unit='deg', frame='icrs')
                world_coords_x = np.array([p1['world_ra'], p2['world_ra']]) * u.deg
                world_coords_y = np.array([p1['world_dec'], p2['world_dec']]) * u.deg

                if self.app._align_by.lower() == 'wcs':
                    plot_x, plot_y = world_coords_x.value, world_coords_y.value
                    dist_str = f"{c1.separation(c2).to(u.arcsec).value:.2f} arcsec"
                else:  # Aligned by pixels
                    plot_x, plot_y = viewer.state.reference_data.coords.world_to_pixel_values(
                        world_coords_x, world_coords_y
                    )
                    dist_str = f"{np.sqrt((plot_x[1]-plot_x[0])**2 + (plot_y[1]-plot_y[0])**2):.2f} pix"

                dist_measure.update_points(plot_x[0], plot_y[0], plot_x[1], plot_y[1], text=dist_str)
                dist_measure.visible = True
            except Exception:
                dist_measure.visible = False

    def _add_distance_row(self, p1, p2):
        """
        Adds a single row to the distances table with the results
        of a distance measurement.
        """
        world_avail = ('world_ra' in p1 and 'world_ra' in p2 and
                       p1.get('world_ra') is not None and p2.get('world_ra') is not None and
                       np.all(np.isfinite([p1['world_ra'], p1['world_dec'],
                                           p2['world_ra'], p2['world_dec']])))

        if world_avail:
            c1 = SkyCoord(p1['world_ra'], p1['world_dec'], unit='deg', frame='icrs')
            c2 = SkyCoord(p2['world_ra'], p2['world_dec'], unit='deg', frame='icrs')
            sep_arcsec = c1.separation(c2).arcsec
            pos_angle = c1.position_angle(c2).deg
            start_ra, start_dec = p1['world_ra'], p1['world_dec']
            end_ra, end_dec = p2['world_ra'], p2['world_dec']
        else:
            sep_arcsec, pos_angle, start_ra, start_dec, end_ra, end_dec = (np.nan,) * 6

        dist_pix = np.sqrt((p2.get('pixel_x', 0) - p1.get('pixel_x', 0))**2 +
                           (p2.get('pixel_y', 0) - p1.get('pixel_y', 0))**2)

        self.distances_table.add_item({
            'Start RA': f"{start_ra:.4f}" if not np.isnan(start_ra) else "N/A",
            'Start Dec': f"{start_dec:.4f}" if not np.isnan(start_dec) else "N/A",
            'End RA': f"{end_ra:.4f}" if not np.isnan(end_ra) else "N/A",
            'End Dec': f"{end_dec:.4f}" if not np.isnan(end_dec) else "N/A",
            'Separation (arcsec)': f"{sep_arcsec:.4f}" if not np.isnan(sep_arcsec) else "N/A",
            'Distance (pix)': f"{dist_pix:.2f}",
            'Position Angle (deg)': f"{pos_angle:.2f}" if not np.isnan(pos_angle) else "N/A"
        })

    def _get_snap_coordinates(self, viewer):
        """
        Finds the permanent marker in the table closest to the cursor's
        current position in the viewer.
        """
        viewer_mark = self._get_mark(viewer)
        cursor_coords = self.coords_info.as_dict()
        cursor_x, cursor_y = cursor_coords.get('axes_x'), cursor_coords.get('axes_y')
        if not len(viewer_mark.x) or cursor_x is None:
            return cursor_coords
        
        marker_xs, marker_ys = viewer_mark.x, viewer_mark.y
        distances_sq = (marker_xs - cursor_x)**2 + (marker_ys - cursor_y)**2
        closest_marker_index_in_viewer = np.argmin(distances_sq)
        
        viewer_id = viewer.reference if viewer.reference is not None else viewer.reference_id
        viewer_loaded_data = [lyr.layer.label for lyr in viewer.layers]
        
        all_items_table = self.table.export_table()
        if all_items_table is None:
            return cursor_coords

        in_viewer_indices = [
            i for i, item in enumerate(all_items_table)
            if item['viewer'] == viewer_id and item['data_label'] in viewer_loaded_data
        ]
        
        if not in_viewer_indices:
            return cursor_coords

        snapped_table_index = in_viewer_indices[closest_marker_index_in_viewer]
        snapped_row = all_items_table[snapped_table_index]

        snapped_axes_x = viewer_mark.x[closest_marker_index_in_viewer]
        snapped_axes_y = viewer_mark.y[closest_marker_index_in_viewer]
        
        snapped_coords = {
            'pixel_x': snapped_row['pixel_x'],
            'pixel_y': snapped_row['pixel_y'],
            'world_ra': snapped_row['world_ra'],
            'world_dec': snapped_row['world_dec'],
            'value': snapped_row['value'],
            'axes_x': snapped_axes_x,
            'axes_y': snapped_axes_y,
            'world:unreliable': snapped_row.get('world:unreliable'),
            'pixel:unreliable': snapped_row.get('pixel:unreliable')
        }
        return snapped_coords
    
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
    
    @traitlets.observe('is_active')
    def _on_is_active_changed(self, *args):
        if self.disabled_msg:
            return
            
        for mark in self.marks.values():
            mark.visible = self.is_active
            
        for dist_measure in self._distance_marks.values():
            dist_measure.visible = self.is_active
            
        for viewer in self.app._viewer_store.values():
            if not hasattr(viewer, 'figure'):
                continue
            callback = self._viewer_callback(viewer, self._on_viewer_key_event)
            
            if self.is_active:
                viewer.add_event_callback(callback, events=['keydown'])
            else:
                viewer.remove_event_callback(callback)
    
    # this is where items are being added to the table
    def _on_viewer_key_event(self, viewer, data):
        if data['event'] == 'keydown' and data['key'] == 'm':
            row_info = self.coords_info.as_dict()
            if 'viewer' in self.table.headers_avail:
                row_info['viewer'] = viewer.reference if viewer.reference is not None else viewer.reference_id # noqa

            for k in self.table.headers_avail:
                row_info.setdefault(k, self._default_table_values.get(k, ''))

            try:
                # if the pixel values are unreliable, set their table values as nan
                row_item_to_add = {k: float('nan') if row_info.get('pixel:unreliable', False) and
                                 k.startswith('pixel_') else v
                                 for k, v in row_info.items()
                                 if k in self.table.headers_avail}
                self.table.add_item(row_item_to_add)
            except ValueError as err: #pragma: no cover
                raise ValueError(f'failed to add {row_info} to table: {repr(err)}')

            x, y = row_info['axes_x'], row_info['axes_y']
            self._get_mark(viewer).append_xy(getattr(x, 'value', x), getattr(y, 'value', y))

            self.hub.broadcast(MarkersPluginUpdate(table_length=len(self.table.items), sender=self))

        elif data['event'] == 'keydown' and data['key'] == 'r':
            self.table.clear_table()

        elif data['event'] == 'keydown' and data.get('key') in ('d', '∂'):
            if data.get('altKey', False):
                coords = self._get_snap_coordinates(viewer)
            else:
                coords = self.coords_info.as_dict()
            viewer_id = viewer.reference or viewer.reference_id

            if self._distance_first_point is None:
                self._distance_first_point = coords
                if viewer_id in self._distance_marks:
                    self._distance_marks[viewer_id].visible = False
                self._distance_line_endpoints = None
            else:
                p1 = self._distance_first_point
                p2 = coords

                world_avail = ('world_ra' in p1 and 'world_ra' in p2 and
                               p1.get('world_ra') is not None and p2.get('world_ra') is not None and
                               not p1.get('world:unreliable', True) and
                               not p2.get('world:unreliable', True) and
                               np.all(np.isfinite([p1.get('world_ra', np.nan), p1.get('world_dec', np.nan),
                                                   p2.get('world_ra', np.nan), p2.get('world_dec', np.nan)])))

                if self.app._align_by.lower() == 'wcs' and world_avail:
                    c1 = SkyCoord(p1['world_ra'], p1['world_dec'], unit='deg', frame='icrs')
                    c2 = SkyCoord(p2['world_ra'], p2['world_dec'], unit='deg', frame='icrs')
                    dist = c1.separation(c2)
                    display_str = f"{dist.to(u.arcsec).value:.2f} arcsec"
                else:
                    dist_pix = np.sqrt((p2.get('pixel_x', 0) - p1.get('pixel_x', 0))**2 +
                                       (p2.get('pixel_y', 0) - p1.get('pixel_y', 0))**2)
                    display_str = f"{dist_pix:.2f} pix"

                self.distance_display = display_str

                self._add_distance_row(p1, p2)

                plot_x0, plot_y0 = p1.get('axes_x'), p1.get('axes_y')
                plot_x1, plot_y1 = p2.get('axes_x'), p2.get('axes_y')

                if None in (plot_x0, plot_y0, plot_x1, plot_y1):
                    return

                if viewer_id not in self._distance_marks:
                    dist_measure = DistanceMeasurement(viewer, plot_x0, plot_y0, plot_x1, plot_y1, text=display_str)
                    self._distance_marks[viewer_id] = dist_measure
                    viewer.figure.marks = viewer.figure.marks + dist_measure.marks
                else:
                    dist_measure = self._distance_marks[viewer_id]
                    dist_measure.update_points(plot_x0, plot_y0, plot_x1, plot_y1, text=display_str)
                    dist_measure.visible = True

                self._distance_line_endpoints = {'p1': p1, 'p2': p2}
                self._distance_first_point = None

