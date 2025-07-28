import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from traitlets import Bool, Unicode, Instance, observe, default
import ipywidgets as widgets

from jdaviz.core.events import (ViewerAddedMessage, ChangeRefDataMessage,
                                AddDataMessage, RemoveDataMessage, MarkersPluginUpdate,
                                GlobalDisplayUnitChanged)
from jdaviz.core.marks import MarkersMark, DistanceMeasurement
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin, ViewerSelectMixin, TableMixin,
                                        Table, _is_image_viewer)
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
    template_file = __file__, "markers.vue"
    uses_active_status = Bool(True).tag(sync=True)
    distance_display = Unicode("N/A").tag(sync=True)
    measurements_table = Instance(Table).tag(sync=True, **widgets.widget_serialization)

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
            headers = ['spectral_axis', 'spectral_axis:unit',
                       'slice', 'pixel_x', 'pixel_y',
                       'world_ra', 'world_dec', 'value', 'value:unit', 'viewer']

        elif self.config == 'imviz':
            headers = ['pixel_x', 'pixel_y', 'pixel:unreliable',
                       'world_ra', 'world_dec', 'world:unreliable',
                       'value', 'value:unit', 'value:unreliable',
                       'viewer']

        elif self.config == 'specviz':
            headers = ['spectral_axis', 'spectral_axis:unit',
                       'index', 'value', 'value:unit', 'viewer']

        elif self.config in ('specviz2d'):
            # TODO: add "index" if/when specviz2d supports plotting spectral_axis
            headers = ['spectral_axis', 'spectral_axis:unit',
                       'pixel_x', 'pixel_y', 'value', 'value:unit', 'viewer']

        elif self.config == 'mosviz':
            headers = ['spectral_axis', 'spectral_axis:unit',
                       'pixel_x', 'pixel_y', 'world_ra', 'world_dec', 'index',
                       'value', 'value:unit', 'viewer']
        elif self.config == 'deconfigged':
            # for now combination of specviz2d + imviz (will eventually need more)
            headers = ['spectral_axis', 'spectral_axis:unit',
                       'pixel_x', 'pixel_y', 'pixel:unreliable',
                       'world_ra', 'world_dec', 'world:unreliable',
                       'value', 'value:unit', 'value:unreliable',
                       'viewer']
        else:
            # allow downstream configs to override headers
            headers = kwargs.get('headers', [])

        headers += ['data_label']
        self.table.headers_avail = headers
        self.table.headers_visible = headers
        self.table._default_values_by_colname = self._default_table_values

        self._distance_marks = {}
        self._distance_first_point = None
        self._temporary_dist_measure = None
        self._viewer_for_drawing = None

        # Set the callbacks for each table's clear button
        self.table._clear_callback = self._clear_markers_table_callback
        self.measurements_table._clear_callback = self._clear_measurements_table_callback

        # subscribe to mouse events on any new viewers
        self.hub.subscribe(self, ViewerAddedMessage, handler=self._on_viewer_added)

        # account for image rotation due to a change in reference data
        # and reset distance tool if orientation changes mid-measurement
        self.hub.subscribe(self, ChangeRefDataMessage,
                           handler=self._on_alignment_change)

        # enable/disable mark based on whether parent data entry is in viewer
        self.hub.subscribe(self, AddDataMessage,
                           handler=lambda msg: self._recompute_mark_positions(msg.viewer))
        self.hub.subscribe(self, RemoveDataMessage,
                           handler=lambda msg: self._recompute_mark_positions(msg.viewer))

        self.hub.subscribe(self, GlobalDisplayUnitChanged,
                           handler=self._on_units_changed)

        self.docs_description = """Press 'm' with the cursor over a viewer to log
                                 the mouseover information. To change the
                                 selected layer, click the layer cycler in the
                                 mouseover information section of the app-level
                                 toolbar.
                                 Press 'd' twice to measure the distance between any two points.
                                 Hold the 'Option'(Mac) or 'Alt' key while pressing 'd' to snap
                                 measurement points to the nearest marker."""
        # description displayed under plugin title in tray
        self._plugin_description = 'Create markers on viewers.'

    def _on_units_changed(self, msg=None):
        """
        Callback for when the global display units are changed.
        This clears all distance measurements to prevent them from being
        displayed in the wrong locations.
        """
        if len(self._distance_marks) > 0:
            # The clear_table method handles clearing both the UI table
            # and the marks from all viewers.
            self.measurements_table.clear_table()

    @default('measurements_table')
    def _default_measurements_table(self):
        table = Table(
            self,
            name='measurements_table',
            title='Measurements',
            headers=['Start RA', 'Start Dec', 'End RA', 'End Dec',
                     'Separation (arcsec)', 'Distance (pix)', 'Position Angle (deg)',
                     'Start X', 'End X', 'Start Y', 'End Y',
                     'Δx', 'Δy', 'Viewer', 'Data Label'],
        )
        return table

    def _on_alignment_change(self, msg=None):
        """
        Resets the distance measurement tool if the orientation changes
        while a measurement is in progress.
        """
        if self._distance_first_point is not None:
            # If we are in the middle of drawing, clean up the temporary marks
            if self._temporary_dist_measure is not None and self._viewer_for_drawing is not None:
                self._viewer_for_drawing.remove_event_callback(self._on_mouse_move_while_drawing)
                temp_marks = self._temporary_dist_measure.marks
                self._viewer_for_drawing.figure.marks = [
                    m for m in self._viewer_for_drawing.figure.marks if m not in temp_marks
                ]
                self._temporary_dist_measure = None
                self._viewer_for_drawing = None

            self._distance_first_point = None
            self.distance_display = "N/A"
        if msg is not None:
            self._recompute_mark_positions(msg.viewer)

    def _clear_markers_table_callback(self, *args):
        """
        Callback for the clear button on the main markers table.
        This clears all 'm' key marks from all viewers.
        """
        for mark in self.marks.values():
            mark.clear()

        # The only job here is to announce that the table is empty.
        self.hub.broadcast(MarkersPluginUpdate(table_length=0, sender=self))

    def _clear_measurements_table_callback(self, *args):
        """
        Callback for the clear button on the measurements table.
        This clears all 'd' key distance lines from all viewers.
        """
        all_dist_marks = set()
        for dist_measures in self._distance_marks.values():
            for dm in dist_measures:
                all_dist_marks.update(dm.marks)

        # Iterate through all viewers in the app and remove any distance marks found.
        for viewer in self.app._viewer_store.values():
            if not hasattr(viewer, 'figure'):
                continue
            viewer.figure.marks = [m for m in viewer.figure.marks if m not in all_dist_marks]
        self._distance_marks.clear()
        self.distance_display = "N/A"
        self._distance_first_point = None

    @observe('table.items')
    def _sync_markers_from_table(self, *args):
        """
        Observer callback that redraws all marks when the markers table changes
        (e.g., a row is deleted) to ensure the plot and table are synchronized.
        """
        for viewer in self.app._viewer_store.values():
            if hasattr(viewer, 'figure'):
                self._recompute_mark_positions(viewer)

    def _create_viewer_callbacks(self, viewer):
        if not self.is_active:
            return
        callback = self._viewer_callback(viewer, self._on_viewer_key_event)
        viewer.add_event_callback(callback, events=['keydown'])

    def _on_viewer_added(self, msg):
        self._create_viewer_callbacks(self.app.get_viewer_by_id(msg.viewer_id))

    def _recompute_mark_positions(self, viewer):
        if self.table is None or self.table._qtable is None:
            return
        if 'world_ra' not in self.table.headers_avail:
            return
        viewer_id = viewer.reference if viewer.reference is not None else viewer.reference_id
        viewer_loaded_data = [lyr.layer.label for lyr in viewer.layers]
        data_labels = self.table._qtable['data_label']
        viewer_labels = self.table._qtable['viewer']
        # note: could eventually have a user-provided switch to show markers in other viewers
        # by just skipping this first viewer_label == viewer_id check
        in_viewer = [viewer_label == viewer_id and data_label in viewer_loaded_data
                     for viewer_label, data_label in zip(viewer_labels, data_labels)]
        viewer_mark = self._get_mark(viewer)
        if not np.any(in_viewer):
            viewer_mark.x, viewer_mark.y = [], []
            return

        if self.app._align_by.lower() == 'wcs':
            # convert from the sky coordinates in the table to pixels via the WCS of the current
            # reference data
            orig_world_x = np.asarray(self.table._qtable['world_ra'][in_viewer])
            orig_world_y = np.asarray(self.table._qtable['world_dec'][in_viewer])
            pixel_unreliable = np.asarray(self.table._qtable['pixel:unreliable'][in_viewer])
            new_wcs = viewer.state.reference_data.coords
            try:
                new_x, new_y = new_wcs.world_to_pixel_values(orig_world_x*u.deg,
                                                             orig_world_y*u.deg)
                for coord in [new_x, new_y]:
                    coord[pixel_unreliable] = np.nan
            except Exception:
                # fail gracefully
                new_x, new_y = [], []

        elif self.app._align_by.lower() == 'pixels':
            # When aligning by pixels, we can just use the pixel coordinates
            # that were stored in the table when the marks were created.
            new_x = np.asarray(self.table._qtable['pixel_x'][in_viewer])
            new_y = np.asarray(self.table._qtable['pixel_y'][in_viewer])

        else:
            raise NotImplementedError(f"align_by {self.app._align_by} not implemented")

        # check for entries that do not correspond to a layer or only have pixel coordinates
        pixel_only_inds = data_labels == ''
        if np.any(pixel_only_inds):
            # TODO: should we rescale these since pixel coordinates when aligned by WCS are always
            # on the range 0-1 because of the orientation layer? Or hide the pixel option in the
            # cycler when WCS-linked?
            pixel_x = np.asarray(self.table._qtable['pixel_x'])
            pixel_y = np.asarray(self.table._qtable['pixel_y'])
            new_x = np.append(new_x, pixel_x[pixel_only_inds])
            new_y = np.append(new_y, pixel_y[pixel_only_inds])

        viewer_mark.x, viewer_mark.y = new_x, new_y

    def _add_sky_distance_row(self, p1, p2, viewer):
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
        viewer_id = viewer.reference or viewer.reference_id
        data_label = p1.get('data_label', 'N/A')

        row_data = {
            'Start RA': f"{start_ra:.4f}" if not np.isnan(start_ra) else "N/A",
            'Start Dec': f"{start_dec:.4f}" if not np.isnan(start_dec) else "N/A",
            'End RA': f"{end_ra:.4f}" if not np.isnan(end_ra) else "N/A",
            'End Dec': f"{end_dec:.4f}" if not np.isnan(end_dec) else "N/A",
            'Separation (arcsec)': f"{sep_arcsec:.4f}" if not np.isnan(sep_arcsec) else "N/A",
            'Distance (pix)': f"{dist_pix:.2f}",
            'Position Angle (deg)': f"{pos_angle:.2f}" if not np.isnan(pos_angle) else "N/A",
            'Viewer': viewer_id,
            'Data Label': data_label
        }
        self.measurements_table.add_item(row_data)

    def _add_profile_distance_row(self, p1, p2, viewer, dx, dy, x_unit, y_unit):
        """Adds a single row to the measurements table for a profile-based distance."""
        viewer_id = viewer.reference or viewer.reference_id
        data_label = p1.get('data_label', 'N/A')

        # Get start/end coordinates from the point dictionaries
        start_x = p1.get('axes_x', 0)
        end_x = p2.get('axes_x', 0)
        start_y = p1.get('axes_y', 0)
        end_y = p2.get('axes_y', 0)

        row_data = {
            'Start X': f"{start_x:.4g} {x_unit}",
            'End X': f"{end_x:.4g} {x_unit}",
            'Start Y': f"{start_y:.4g} {y_unit}",
            'End Y': f"{end_y:.4g} {y_unit}",
            'Δx': f"{dx:.4g} {x_unit}",
            'Δy': f"{dy:.4g} {y_unit}",
            'Viewer': viewer_id,
            'Data Label': data_label
        }
        self.measurements_table.add_item(row_data)

    def _calculate_distance_text(self, p1, p2, viewer, add_row=False):
        """
        Helper function to calculate the distance between two points and
        generate the appropriate display text. Optionally adds a row to the
        measurements table.
        """
        is_profile = not _is_image_viewer(viewer)

        if is_profile:
            dx_val = p2.get('axes_x', 0) - p1.get('axes_x', 0)
            dy_val = p2.get('axes_y', 0) - p1.get('axes_y', 0)
            x_unit = p1.get('axes_x:unit', '')
            y_unit = p1.get('axes_y:unit', '')
            text_ui = f"Δx: {dx_val:.4g} {x_unit}, Δy: {dy_val:.4g} {y_unit}"
            text_plot = ""
            if add_row:
                self._add_profile_distance_row(p1, p2, viewer, dx_val, dy_val, x_unit, y_unit)
        else:  # Assume image viewer
            world_avail = ('world_ra' in p1 and 'world_ra' in p2 and
                           p1.get('world_ra') is not None and p2.get('world_ra') is not None and
                           np.all(np.isfinite([p1['world_ra'], p1['world_dec'],
                                               p2['world_ra'], p2['world_dec']])))
            if self.config == 'imviz' and self.app._align_by.lower() == 'pixels':
                dist_pix = np.sqrt((p2.get('pixel_x', 0) - p1.get('pixel_x', 0))**2 +
                                   (p2.get('pixel_y', 0) - p1.get('pixel_y', 0))**2)
                text_plot = f"{dist_pix:.2f} pix"
            elif world_avail:
                c1 = SkyCoord(p1['world_ra'], p1['world_dec'], unit='deg', frame='icrs')
                c2 = SkyCoord(p2['world_ra'], p2['world_dec'], unit='deg', frame='icrs')
                text_plot = f"{c1.separation(c2).to(u.arcsec).value:.2f} arcsec"
            else:
                dist_pix = np.sqrt((p2.get('pixel_x', 0) - p1.get('pixel_x', 0))**2 +
                                   (p2.get('pixel_y', 0) - p1.get('pixel_y', 0))**2)
                text_plot = f"{dist_pix:.2f} pix"
            text_ui = text_plot
            if add_row:
                self._add_sky_distance_row(p1, p2, viewer)

        return text_ui, text_plot

    def _get_snap_coordinates(self, viewer):
        viewer_mark = self._get_mark(viewer)
        cursor_coords = self.coords_info.as_dict()
        cursor_x, cursor_y = cursor_coords.get('axes_x'), cursor_coords.get('axes_y')

        if not len(viewer_mark.x) or cursor_x is None or cursor_y is None:
            return cursor_coords

        marker_xs, marker_ys = viewer_mark.x, viewer_mark.y
        distances_sq = None

        if ('x' in viewer.scales and 'y' in viewer.scales and
                hasattr(viewer.scales['x'], 'domain') and hasattr(viewer.scales['x'], 'range') and
                hasattr(viewer.scales['y'], 'domain') and hasattr(viewer.scales['y'], 'range')):

            x_scale = viewer.scales['x']
            y_scale = viewer.scales['y']

            x_pixel_span = abs(x_scale.range[1] - x_scale.range[0])
            y_pixel_span = abs(y_scale.range[1] - y_scale.range[0])

            if x_pixel_span > 0 and y_pixel_span > 0:
                x_domain_span = x_scale.domain[1] - x_scale.domain[0]
                x_units_per_px = x_domain_span / x_pixel_span

                y_domain_span = y_scale.domain[1] - y_scale.domain[0]
                y_units_per_px = y_domain_span / y_pixel_span

                dx_pix = (marker_xs - cursor_x) / x_units_per_px
                dy_pix = (marker_ys - cursor_y) / y_units_per_px

                # Use 1D distance for spectrum viewers
                if not _is_image_viewer(viewer):
                    # For spectrum viewers, only consider the distance along the spectral axis.
                    distances_sq = dx_pix**2
                else:
                    # For image viewers, consider the 2d distance.
                    distances_sq = dx_pix**2 + dy_pix**2

        # If the preferred method was not possible or failed, use the fallback.
        if distances_sq is None:
            try:
                x_data_range = viewer.state.x_max - viewer.state.x_min
                y_data_range = viewer.state.y_max - viewer.state.y_min

                if not x_data_range or not y_data_range:
                    return cursor_coords

                norm_dx = (marker_xs - cursor_x) / x_data_range
                norm_dy = (marker_ys - cursor_y) / y_data_range

                if not _is_image_viewer(viewer):
                    distances_sq = norm_dx**2
                else:
                    distances_sq = norm_dx**2 + norm_dy**2

            except Exception:
                # If all else fails, do not snap
                return cursor_coords

        if distances_sq is None:
            # This case would be hit if both primary and fallback methods fail.
            return cursor_coords

        # Find the closest marker using the calculated distances.
        closest_marker_index_in_viewer = np.nanargmin(distances_sq)
        viewer_id = viewer.reference if viewer.reference is not None else viewer.reference_id
        viewer_loaded_data = [lyr.layer.label for lyr in viewer.layers]
        all_items_table = self.table.export_table()

        if all_items_table is None:
            return cursor_coords

        in_viewer_indices = [
            i for i, item in enumerate(all_items_table)
            if item.get('viewer') == viewer_id and item.get('data_label') in viewer_loaded_data
        ]

        if not in_viewer_indices or closest_marker_index_in_viewer >= len(in_viewer_indices):
            return cursor_coords

        snapped_table_index = in_viewer_indices[closest_marker_index_in_viewer]
        snapped_row = all_items_table[snapped_table_index]

        snapped_coords = {k: snapped_row.get(k) for k in self.table.headers_avail}
        snapped_coords['axes_x'] = viewer_mark.x[closest_marker_index_in_viewer]
        snapped_coords['axes_y'] = viewer_mark.y[closest_marker_index_in_viewer]
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

    @observe('is_active')
    def _on_is_active_changed(self, *args):
        if self.disabled_msg:
            return

        # toggle visibility of markers
        for mark in self.marks.values():
            mark.visible = self.is_active

        # subscribe/unsubscribe to keypress events across all viewers
        for viewer_marks in self._distance_marks.values():
            for mark in viewer_marks:
                mark.visible = self.is_active

        for viewer in self.app._viewer_store.values():
            if not hasattr(viewer, 'figure'):
                # table viewer, etc
                continue

            callback = self._viewer_callback(viewer, self._on_viewer_key_event)
            if self.is_active:
                viewer.add_event_callback(callback, events=['keydown'])
            else:
                viewer.remove_event_callback(callback)

    def _on_mouse_move_while_drawing(self, event):
        """
        Callback for 'mousemove' event. Updates the temporary DistanceMeasurement
        mark to follow the cursor.
        """
        if self._temporary_dist_measure is None or self._distance_first_point is None:
            return

        p1 = self._distance_first_point
        p2 = self.coords_info.as_dict()

        text_ui, text_plot = self._calculate_distance_text(p1, p2, self._viewer_for_drawing)
        self.distance_display = text_ui

        self._temporary_dist_measure.update_points(
            p1.get('axes_x'), p1.get('axes_y'),
            event['domain']['x'], event['domain']['y'],
            text=text_plot
        )

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
                self.hub.broadcast(MarkersPluginUpdate(table_length=len(self.table), sender=self))

            except ValueError as err:  # pragma: no cover
                raise ValueError(f'failed to add {row_info} to table: {repr(err)}')
            x, y = row_info['axes_x'], row_info['axes_y']
            self._get_mark(viewer).append_xy(getattr(x, 'value', x), getattr(y, 'value', y))

        # on mac 'option + d' gets transmitted as delta instead of just d + alt
        elif data['event'] == 'keydown' and data.get('key') in ('d', '∂'):
            if data.get('altKey', False):
                coords = self._get_snap_coordinates(viewer)
            else:
                coords = self.coords_info.as_dict()
            viewer_id = viewer.reference or viewer.reference_id

            if self._distance_first_point is None:
                self._distance_first_point = coords
                self.distance_display = "..."
                self._viewer_for_drawing = viewer
                start_x, start_y = coords.get('axes_x'), coords.get('axes_y')

                is_profile = not _is_image_viewer(viewer)
                preview_text = "" if is_profile else "..."

                self._temporary_dist_measure = DistanceMeasurement(
                    viewer, start_x, start_y, start_x, start_y, text=preview_text
                )
                self._temporary_dist_measure.label_shadow.visible = False
                for mark in self._temporary_dist_measure.marks:
                    mark.opacities = [0.9]

                viewer.figure.marks = viewer.figure.marks + self._temporary_dist_measure.marks
                viewer.add_event_callback(self._on_mouse_move_while_drawing,
                                          events=['mousemove'])
            else:
                viewer.remove_event_callback(self._on_mouse_move_while_drawing)

                if self._temporary_dist_measure:
                    temp_marks = self._temporary_dist_measure.marks
                    viewer.figure.marks = [
                        m for m in viewer.figure.marks if m not in temp_marks
                    ]
                self._temporary_dist_measure = None

                p1 = self._distance_first_point
                p2 = coords
                self._distance_first_point = None

                text_ui, text_plot = self._calculate_distance_text(p1, p2, viewer, add_row=True)
                self.distance_display = text_ui

                plot_x0, plot_y0 = p1.get('axes_x'), p1.get('axes_y')
                plot_x1, plot_y1 = p2.get('axes_x'), p2.get('axes_y')

                if None in (plot_x0, plot_y0, plot_x1, plot_y1):
                    self.distance_display = "N/A"
                    self._viewer_for_drawing = None
                    return

                dist_measure = DistanceMeasurement(viewer, plot_x0, plot_y0,
                                                   plot_x1, plot_y1,
                                                   text=text_plot)
                dist_measure.endpoints = {'p1': p1, 'p2': p2}
                self._distance_marks.setdefault(viewer_id, []).append(dist_measure)
                viewer.figure.marks = viewer.figure.marks + dist_measure.marks

                self._viewer_for_drawing = None
