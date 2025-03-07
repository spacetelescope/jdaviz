import numpy as np
from astropy import units as u
from astropy.table import QTable, Table as AstropyTable
from astropy.coordinates import SkyCoord
from echo import delay_callback
from traitlets import List, Unicode, Bool, Int, observe

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin, ViewerSelectMixin,
                                        FileImportSelectPluginComponent, HasFileImportSelect,
                                        with_spinner)
from jdaviz.core.custom_traitlets import IntHandleEmpty
from jdaviz.core.events import CatalogResultsChangedMessage, CatalogSelectClickEventMessage
from jdaviz.core.marks import CatalogMark
from jdaviz.core.template_mixin import Table, TableMixin
from jdaviz.core.user_api import PluginUserApi
from jdaviz.utils import get_top_layer_index

__all__ = ['Catalogs']


@tray_registry('imviz-catalogs', label="Catalog Search")
class Catalogs(PluginTemplateMixin, ViewerSelectMixin, HasFileImportSelect, TableMixin):
    """
    See the :ref:`Catalog Search Plugin Documentation <imviz-catalogs>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.close_in_tray`
    * :meth:`zoom_to_selected`
    """
    template_file = __file__, "catalogs.vue"
    uses_active_status = Bool(True).tag(sync=True)
    catalog_items = List([]).tag(sync=True)
    catalog_selected = Unicode("").tag(sync=True)
    results_available = Bool(False).tag(sync=True)
    number_of_results = Int(0).tag(sync=True)
    max_sources = IntHandleEmpty(1000).tag(sync=True)

    # setting the default table headers and values
    _default_table_values = {
            'Right Ascension (degrees)': np.nan,
            'Declination (degrees)': np.nan,
            'Object ID': np.nan,
            'id': np.nan,
            'x_coord': np.nan,
            'y_coord': np.nan
            }

    headers = ['Right Ascension (degrees)', 'Declination (degrees)',
               'Object ID', 'x_coord', 'y_coord']

    table_selected_widget = Unicode().tag(sync=True)

    @property
    def user_api(self):
        return PluginUserApi(self, expose=('clear_table', 'export_table', 'import_catalog',
                                           'zoom_to_selected', 'select_rows',
                                           'select_all', 'select_none'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # description displayed under plugin title in tray
        self._plugin_description = 'Query catalog for objects within region on sky.'

        cat_options = ['SDSS', 'Gaia']
        if not self.app.state.settings.get('server_is_remote', False):
            cat_options.append('From File...')
        self.catalog = FileImportSelectPluginComponent(self,
                                                       items='catalog_items',
                                                       selected='catalog_selected',
                                                       manual_options=cat_options)

        # set the custom file parser for importing catalogs
        self.catalog._file_parser = self._file_parser
        self._marker_name = 'catalog_results'

        # initializing the headers in the table that is displayed in the UI
        self.table.headers_avail = self.headers
        self.table.headers_visible = self.headers
        self.table._default_values_by_colname = self._default_table_values
        self.table._selected_rows_changed_callback = self._table_selection_changed
        # note: `item_key` is the name of a column in the
        # table that has unique values for in row
        self.table.item_key = 'id'
        self.table.show_rowselect = True

        def clear_table_callback():
            # gets the current viewer
            viewer = self.viewer.selected_obj

            # resetting values
            self.results_available = False
            self.number_of_results = 0

            if self._marker_name in self.app.data_collection.labels:
                # all markers are removed from the viewer
                viewer.remove_markers(marker_name=self._marker_name)

        self.table._clear_callback = clear_table_callback

        self.table_selected = Table(self, name='table_selected')
        self.table_selected.clear_btn_lbl = 'Clear Selection'
        self.table_selected.show_if_empty = False

        def clear_selected_table_callback():
            self.table.select_none()

        self.table_selected._clear_callback = clear_selected_table_callback
        self.table_selected_widget = 'IPY_MODEL_'+self.table_selected.model_id

        self.docs_description = "Queries an area encompassed by the viewer using\
                                 a specified catalog and marks all the objects\
                                 found within the area."

        self.session.hub.subscribe(self, CatalogSelectClickEventMessage,
                                   self._on_catalog_select_click_event)

    @staticmethod
    def _file_parser(path):
        if isinstance(path, AstropyTable):  # includes QTable
            from_file_string = f'API: {path.__class__.__name__} object'
            return '', {from_file_string: path}

        try:
            table = QTable.read(path)
        except Exception:
            return 'Could not parse file with astropy.table.QTable.read', {}

        if not table.colnames:  # Ensure the file has columns
            return "File contains no columns", {}

        if 'sky_centroid' not in table.colnames:
            return 'Table does not contain required sky_centroid column', {}

        return '', {path: table}

    def _on_catalog_select_click_event(self, msg):
        xs, ys = self.table._qtable['x_coord'], self.table._qtable['y_coord']
        # nearest point
        distsq = (xs - msg.x)**2 + (ys - msg.y)**2
        ind = np.argmin(distsq)
        item = self.table.items[ind]
        if item in self.table.selected_rows:
            self.table.selected_rows = [sr for sr in self.table.selected_rows if sr != item]
        else:
            self.table.selected_rows += [item]
        self._table_selection_changed()

    @with_spinner()
    def search(self, error_on_fail=False):
        """Search the catalog, display markers on the viewer, and return results if available.

        Parameters
        ----------
        error_on_fail : bool
            Throw exception when query fails instead of a red snackbar message.
            This is useful for debugging.

        Returns
        -------
        skycoords : `~astropy.coordinates.SkyCoord` or `None`
            Sky coordinates (or None if no results available).

        """
        # calling clear in the case the user forgot after searching
        self.clear_table()

        # gets the current viewer
        viewer = self.viewer.selected_obj

        # nothing happens in the case there is no image in the viewer
        # additionally if the data does not have WCS
        if viewer.state.reference_data is None or viewer.state.reference_data.coords is None:
            self.results_available = False
            self.number_of_results = 0
            return
        # obtains the center point of the current image and converts the point into sky coordinates
        x_center = (viewer.state.x_min + viewer.state.x_max) * 0.5
        y_center = (viewer.state.y_min + viewer.state.y_max) * 0.5
        skycoord_center = viewer.state.reference_data.coords.pixel_to_world(x_center, y_center)

        # obtains the viewer's zoom limits based on the visible layer
        ny, nx = viewer.state.reference_data.shape
        zoom_x_min = max(0, viewer.state.x_min)
        zoom_x_max = min(nx, viewer.state.x_max)
        zoom_y_min = max(0, viewer.state.y_min)
        zoom_y_max = min(ny, viewer.state.y_max)
        zoom_coordinate = viewer.state.reference_data.coords.pixel_to_world(
            [zoom_x_min, zoom_x_min, zoom_x_max, zoom_x_max],
            [zoom_y_min, zoom_y_max, zoom_y_max, zoom_y_min])

        # radius for querying the region is based on:
        # the distance between the longest zoom limits and the center point
        zoom_radius = max(skycoord_center.separation(zoom_coordinate))

        max_sources_used = False

        # conducts search based on SDSS
        if self.catalog_selected == "SDSS":
            from astroquery.sdss import SDSS
            r_max = 3 * u.arcmin
            src_id_colname = "objid"

            # queries the region (based on the provided center point and radius)
            # finds all the sources in that region
            try:
                if zoom_radius > r_max:  # SDSS now has radius max limit
                    self.hub.broadcast(SnackbarMessage(
                        f"Radius for {self.catalog_selected} has max radius of {r_max} but got "
                        f"{zoom_radius.to(u.arcmin)}, using {r_max}.",
                        color='warning', sender=self))
                    zoom_radius = r_max
                query_region_result = SDSS.query_region(skycoord_center, radius=zoom_radius,
                                                        data_release=17)
                if len(query_region_result) > self.max_sources:
                    query_region_result = query_region_result[:self.max_sources]
                    max_sources_used = True
            except Exception as e:  # nosec
                errmsg = (f"Failed to query {self.catalog_selected} with c={skycoord_center} and "
                          f"r={zoom_radius}: {repr(e)}")
                if error_on_fail:
                    raise Exception(errmsg) from e
                self.hub.broadcast(SnackbarMessage(errmsg, color='error', sender=self))
                query_region_result = None

            if query_region_result is None:
                self.results_available = True
                self.number_of_results = 0
                self.app._catalog_source_table = None
                viewer.remove_markers(marker_name=self._marker_name)
                return

            # TODO: Filter this table the same way as the actual displayed markers.
            # attach the table to the app for Python extraction
            self.app._catalog_source_table = query_region_result

        elif self.catalog_selected == 'Gaia':
            from astroquery.gaia import Gaia

            Gaia.ROW_LIMIT = self.max_sources
            sources = Gaia.query_object(skycoord_center, radius=zoom_radius,
                                        columns=('source_id', 'ra', 'dec')
                                        )
            if "SOURCE_ID" in sources.colnames:  # Case could flip non-deterministically
                src_id_colname = "SOURCE_ID"
            else:
                src_id_colname = "source_id"
            if len(sources) == self.max_sources:
                max_sources_used = True
            self.app._catalog_source_table = sources

        elif self.catalog_selected == 'From File...':
            # all exceptions when going through the UI should have prevented setting this path
            # but this exceptions might be raised here if setting from_file from the UI
            table = self.catalog.selected_obj
            column_names = table.colnames
            self.table.headers_avail = self.headers + [
                col for col in column_names if col not in self.headers]
            self.table.headers_visible = self.headers
            if len(table['sky_centroid']) > self.max_sources:
                self.app._catalog_source_table = table[:self.max_sources]
                max_sources_used = True
            else:
                self.app._catalog_source_table = table
        else:
            self.results_available = False
            self.number_of_results = 0
            self.app._catalog_source_table = None
            raise NotImplementedError(f"{self.catalog_selected} not a supported catalog")

        self.results_available = True
        if not len(self.app._catalog_source_table):
            self.number_of_results = 0
            self.app._catalog_source_table = None
            return

        if max_sources_used:
            snackbar_message = SnackbarMessage(
                    f"{self.catalog_selected} queried, results returned were limited using max_sources = {self.max_sources}.",  # noqa
                    color="success",
                    sender=self)
            self.hub.broadcast(snackbar_message)

        # Convert to pixel coordinates and filter results to be within viewer bounds
        if self.catalog_selected in ["SDSS", "Gaia"]:
            skycoords = SkyCoord(self.app._catalog_source_table['ra'],
                                 self.app._catalog_source_table['dec'],
                                 unit='deg')
        elif self.catalog_selected in ["From File..."]:
            skycoords = self.app._catalog_source_table['sky_centroid']

        pixel_table = viewer.state.reference_data.coords.world_to_pixel(skycoords)
        self.app._catalog_source_table['x_coord'] = pixel_table[0]
        self.app._catalog_source_table['y_coord'] = pixel_table[1]
        x_coordinates = []
        y_coordinates = []
        source_table = self.app._catalog_source_table
        mask = ((source_table['x_coord'] < zoom_x_min) |
                (source_table['x_coord'] > zoom_x_max) |
                (source_table['y_coord'] < zoom_y_min) |
                (source_table['y_coord'] > zoom_y_max))
        self.app._catalog_source_table = self.app._catalog_source_table[~mask]
        skycoords = skycoords[~mask]

        if self.catalog_selected in ["SDSS", "Gaia"]:
            for row in self.app._catalog_source_table:
                x_coordinates.append(row['x_coord'])
                y_coordinates.append(row['y_coord'])
                row_id = row[src_id_colname]
                # Check if the row contains the required keys
                row_info = {'Right Ascension (degrees)': row['ra'],
                            'Declination (degrees)': row['dec'],
                            'Object ID': row_id.astype(str),
                            'id': len(self.table),
                            'x_coord': row['x_coord'],
                            'y_coord': row['y_coord']}
                self.table.add_item(row_info)

        # NOTE: If performance becomes a problem, see
        # https://docs.astropy.org/en/stable/table/index.html#performance-tips
        elif self.catalog_selected in ["From File..."]:
            for row in self.app._catalog_source_table:  # noqa:E501
                row_info = {
                    'Right Ascension (degrees)': row['sky_centroid'].ra.deg,
                    'Declination (degrees)': row['sky_centroid'].dec.deg,
                    'Object ID': str(row.get('label', f"{len(self.table) + 1}")),
                    'id': len(self.table),
                    'x_coord': row['x_coord'],
                    'y_coord': row['y_coord'],
                }
                x_coordinates.append(row['x_coord'])
                y_coordinates.append(row['y_coord'])
                # Add sky_centroid and label explicitly to row_info
                row_info['sky_centroid'] = row['sky_centroid']
                row_info['label'] = row_info['Object ID']
                for col in table.colnames:
                    if col not in self.headers:  # Skip already processed columns
                        row_info[col] = row[col]

                self.table.add_item(row_info)

        filtered_skycoords = viewer.state.reference_data.coords.pixel_to_world(x_coordinates,
                                                                               y_coordinates)

        # QTable stores all the filtered sky coordinate points to be marked
        catalog_results = QTable({'coord': filtered_skycoords})

        self.number_of_results = len(catalog_results)
        # markers are added to the viewer based on the table
        viewer.marker = {'color': 'blue', 'alpha': 0.8, 'markersize': 30, 'fill': False}
        viewer.add_markers(table=catalog_results, use_skycoord=True, marker_name=self._marker_name)

        msg = CatalogResultsChangedMessage(sender=self)
        self.session.hub.broadcast(msg)

        return skycoords

    def _get_mark(self, viewer):
        matches = [mark for mark in viewer.figure.marks if isinstance(mark, CatalogMark)]
        if len(matches):
            return matches[0]
        mark = CatalogMark(viewer)
        viewer.figure.marks = viewer.figure.marks + [mark]
        return mark

    @property
    def marks(self):
        return {viewer_id: self._get_mark(viewer)
                for viewer_id, viewer in self.app._viewer_store.items()
                if hasattr(viewer, 'figure')}

    @observe('is_active')
    def _on_is_active_changed(self, *args):
        if self.disabled_msg:
            return

        for mark in self.marks.values():
            mark.visible = self.is_active

    def _table_selection_changed(self, msg={}):
        selected_rows = self.table.selected_rows

        self.table_selected._clear_table()
        for selected_row in selected_rows:
            self.table_selected.add_item(selected_row)

        x = [float(coord['x_coord']) for coord in selected_rows]
        y = [float(coord['y_coord']) for coord in selected_rows]
        self._get_mark(self.viewer.selected_obj).update_xy(getattr(x, 'value', x),
                                                           getattr(y, 'value', y))

    def vue_zoom_in(self, *args, **kwargs):
        self.zoom_to_selected()

    def zoom_to_selected(self, padding=0.02, return_bounding_box=False):
        """
        Zoom on the default viewer to a region containing the currently selected
        points in the catalog.

        Parameters
        ----------
        padding : float, optional
            A fractional value representing the padding around the bounding box
            of the selected points. It is applied as a proportion of the largest
            dimension of the current extent of loaded data. Defaults to 0.02.
        return_bounding_box : bool, optional
            If True, returns the bounding box of the zoomed region as
            ((x_min, x_max), (y_min, y_max)). Defaults to False.

        Returns
        -------
        bb : list of float or None
            If there are activley selected rows, and ``return_bounding_box`` is
            True, returns a list containing the bounding
            box coordinates: ``[x_min, x_max, y_min, y_max]``.
            Otherwise, returns `None`.

        """
        viewer = self.viewer.selected_obj  # gets the current viewer

        selected_rows = self.table.selected_rows
        if not selected_rows:  # Check if no rows are selected
            return

        if padding <= 0 or padding > 1:
            raise ValueError("padding must be between 0 (exclusive) and 1 (inclusive).")

        i_top = get_top_layer_index(viewer)
        image = viewer.layers[i_top].layer
        x_min = 99999
        x_max = -99999
        y_min = 99999
        y_max = -99999
        for coord in selected_rows:  # list of dict
            cur_x, cur_y = viewer._get_real_xy(
                image, float(coord['x_coord']), float(coord['y_coord']))[:2]
            if cur_x < x_min:
                x_min = cur_x
            if cur_x > x_max:
                x_max = cur_x
            if cur_y < y_min:
                y_min = cur_y
            if cur_y > y_max:
                y_max = cur_y

        if x_min == x_max and y_min == y_max:  # Only one selected
            pass
        elif x_min >= x_max or y_min >= y_max:
            raise ValueError(
                f"Zoom failed: x_min={x_min}, x_max={x_max}, y_min={y_min}, y_max={y_max}")

        pix_pad = padding * max(x_max, y_max)
        x_min -= pix_pad
        x_max += pix_pad
        y_min -= pix_pad
        y_max += pix_pad
        new_y_min = viewer._get_real_xy(image, x_min, y_min, reverse=True)[1]
        new_y_max = viewer._get_real_xy(image, x_max, y_max, reverse=True)[1]

        # First, we center using image's coordinates.
        viewer.center_on((0.5 * (x_min + x_max), 0.5 * (y_min + y_max)))

        # Then, we zoom using reference data's coordinates. This is important when WCS linked.
        # We cannot use viewer.zoom_level because it is wonky when WCS linked.
        # Given most displays are wider in X, we make sure Y coordinates all fit first
        # and X will naturally all fit within after aspect ratio is taken into account.
        with delay_callback(viewer.state, 'x_min', 'x_max', 'y_min', 'y_max'):
            viewer.state.y_min = new_y_min
            viewer.state.y_max = new_y_max
        viewer.state._adjust_limits_aspect()

        if return_bounding_box:
            return [viewer.state.x_min, viewer.state.x_max, viewer.state.y_min, viewer.state.y_max]

    def import_catalog(self, catalog):
        """
        Import a catalog from a file path.

        Parameters
        ----------
        catalog : str
          Path to a file that can be parsed by astropy QTable
        """
        if isinstance(catalog, str):
            self.catalog.import_file(catalog)
        elif isinstance(catalog, AstropyTable):  # includes QTable
            self.catalog.import_obj(catalog)
        else:  # pragma: no cover
            raise ValueError("catalog must be a string (file path) or Table object")

    def vue_do_search(self, *args, **kwargs):
        # calls self.search() which handles all of the searching logic
        self.search()
