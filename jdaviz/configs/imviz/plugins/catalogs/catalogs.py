import numpy as np
import numpy.ma as ma
from astropy import units as u
from astropy.table import QTable
from astropy.coordinates import SkyCoord
from traitlets import List, Unicode, Bool, Int, observe

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin, ViewerSelectMixin,
                                        FileImportSelectPluginComponent, HasFileImportSelect,
                                        with_spinner)
from jdaviz.core.custom_traitlets import IntHandleEmpty

from jdaviz.core.marks import CatalogMark

from jdaviz.core.template_mixin import TableMixin
from jdaviz.core.user_api import PluginUserApi
from echo import delay_callback


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
    """
    template_file = __file__, "catalogs.vue"
    uses_active_status = Bool(True).tag(sync=True)
    catalog_items = List([]).tag(sync=True)
    catalog_selected = Unicode("").tag(sync=True)
    results_available = Bool(False).tag(sync=True)
    number_of_results = Int(0).tag(sync=True)
    max_gaia_sources = IntHandleEmpty(1000).tag(sync=True)

    # setting the default table headers and values
    _default_table_values = {
            'Right Ascension (degrees)': np.nan,
            'Declination (degrees)': np.nan,
            'Object ID': np.nan,
            'id': np.nan,
            'x_coord': np.nan,
            'y_coord': np.nan}

    @property
    def user_api(self):
        return PluginUserApi(self, expose=('clear_table', 'export_table',))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.catalog = FileImportSelectPluginComponent(self,
                                                       items='catalog_items',
                                                       selected='catalog_selected',
                                                       manual_options=['SDSS', 'Gaia',
                                                                       'From File...'])

        # set the custom file parser for importing catalogs
        self.catalog._file_parser = self._file_parser
        self._marker_name = 'catalog_results'

        # initializing the headers in the table that is displayed in the UI
        headers = ['Right Ascension (degrees)', 'Declination (degrees)',
                   'Object ID', 'x_coord', 'y_coord']

        self.table.headers_avail = headers
        self.table.headers_visible = headers
        self.table._default_values_by_colname = self._default_table_values
        self.table._selected_rows_changed_callback = lambda msg: self.plot_selected_points()
        self.table.item_key = 'id'
        self.table.show_rowselect = True

    @staticmethod
    def _file_parser(path):
        try:
            table = QTable.read(path)
        except Exception:
            return 'Could not parse file with astropy.table.QTable.read', {}

        if 'sky_centroid' not in table.colnames:
            return 'Table does not contain required sky_centroid column', {}

        return '', {path: table}

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
        skycoord_table : `~astropy.coordinates.SkyCoord` or `None`
            Sky coordinates (or None if no results available).

        """
        # calling clear in the case the user forgot after searching
        self.clear()

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

        # conducts search based on SDSS
        if self.catalog_selected == "SDSS":
            from astroquery.sdss import SDSS
            r_max = 3 * u.arcmin

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
            skycoord_table = SkyCoord(query_region_result['ra'],
                                      query_region_result['dec'],
                                      unit='deg')

        elif self.catalog_selected == 'Gaia':
            from astroquery.gaia import Gaia, conf

            with conf.set_temp("ROW_LIMIT", self.max_gaia_sources):
                sources = Gaia.query_object(skycoord_center, radius=zoom_radius,
                                            columns=('source_id', 'ra', 'dec'))
            self.app._catalog_source_table = sources
            skycoord_table = SkyCoord(sources['ra'], sources['dec'], unit='deg')

        elif self.catalog_selected == 'From File...':
            # all exceptions when going through the UI should have prevented setting this path
            # but this exceptions might be raised here if setting from_file from the UI
            table = self.catalog.selected_obj
            self.app._catalog_source_table = table
            skycoord_table = table['sky_centroid']

        else:
            self.results_available = False
            self.number_of_results = 0
            self.app._catalog_source_table = None
            raise NotImplementedError(f"{self.catalog_selected} not a supported catalog")

        self.results_available = True
        if not len(skycoord_table):
            self.number_of_results = 0
            self.app._catalog_source_table = None
            return

        # coordinates found are converted to pixel coordinates
        pixel_table = viewer.state.reference_data.coords.world_to_pixel(skycoord_table)
        # coordinates are filtered out (using a mask) if outside the zoom range
        pair_pixel_table = np.dstack((pixel_table[0], pixel_table[1]))
        # ma.masked_outside removes the coordinates outside the zoom range
        # ma.compress_rows removes any row that has a mask mark
        filtered_table = ma.compress_rows(
            ma.masked_outside(pair_pixel_table, [zoom_x_min, zoom_y_min], [zoom_x_max, zoom_y_max])
            [0])
        # coordinates are split into their respective x and y values
        # then they are converted to sky coordinates
        filtered_pair_pixel_table = np.array(np.hsplit(filtered_table, 2))
        x_coordinates = np.squeeze(filtered_pair_pixel_table[0])
        y_coordinates = np.squeeze(filtered_pair_pixel_table[1])

        if self.catalog_selected in ["SDSS", "Gaia"]:
            for row, x_coord, y_coord in zip(self.app._catalog_source_table,
                                             x_coordinates, y_coordinates):
                if self.catalog_selected == "SDSS":
                    row_id = row["objid"]
                elif self.catalog_selected == "Gaia":
                    row_id = row["SOURCE_ID"]
                # Check if the row contains the required keys
                row_info = {'Right Ascension (degrees)': row['ra'],
                            'Declination (degrees)': row['dec'],
                            'Object ID': row_id.astype(str),
                            'id': len(self.table),
                            'x_coord': x_coord,
                            'y_coord': y_coord}
                self.table.add_item(row_info)

        # NOTE: If performance becomes a problem, see
        # https://docs.astropy.org/en/stable/table/index.html#performance-tips
        if self.catalog_selected == 'From File...':
            for row, x_coord, y_coord in zip(self.app._catalog_source_table,
                                             x_coordinates, y_coordinates):
                # Check if the row contains the required keys
                row_info = {'Right Ascension (degrees)': row['sky_centroid'].ra.deg,
                            'Declination (degrees)': row['sky_centroid'].dec.deg,
                            'Object ID': str(row.get('label', 'N/A')),
                            'id': len(self.table),
                            'x_coord': x_coord,
                            'y_coord': y_coord}

                self.table.add_item(row_info)

        filtered_skycoord_table = viewer.state.reference_data.coords.pixel_to_world(x_coordinates,
                                                                                    y_coordinates)

        # QTable stores all the filtered sky coordinate points to be marked
        catalog_results = QTable({'coord': filtered_skycoord_table})

        self.number_of_results = len(catalog_results)
        # markers are added to the viewer based on the table
        viewer.marker = {'color': 'blue', 'alpha': 0.8, 'markersize': 30, 'fill': False}
        viewer.add_markers(table=catalog_results, use_skycoord=True, marker_name=self._marker_name)
        return skycoord_table

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

    def plot_selected_points(self):
        selected_rows = self.table.selected_rows

        x = [float(coord['x_coord']) for coord in selected_rows]
        y = [float(coord['y_coord']) for coord in selected_rows]
        self._get_mark(self.viewer.selected_obj).update_xy(getattr(x, 'value', x),
                                                           getattr(y, 'value', y))

    def vue_zoom_in(self, *args, **kwargs):
        """This function will zoom into the image based on the selected points"""
        selected_rows = self.table.selected_rows

        x = [float(coord['x_coord']) for coord in selected_rows]
        y = [float(coord['y_coord']) for coord in selected_rows]

        # this works with single selected points
        # zooming when the range is too large is not performing correctly
        x_min = min(x) - 50
        x_max = max(x) + 50
        y_min = min(y) - 50
        y_max = max(y) + 50

        imview = self.app._jdaviz_helper._default_viewer

        with delay_callback(imview.state, 'x_min', 'x_max', 'y_min', 'y_max'):
            imview.state.x_min = x_min
            imview.state.x_max = x_max
            imview.state.y_min = y_min
            imview.state.y_max = y_max

        return (x_min, x_max), (y_min, y_max)

    def import_catalog(self, catalog):
        """
        Import a catalog from a file path.

        Parameters
        ----------
        catalog : str
          Path to a file that can be parsed by astropy QTable
        """
        # TODO: self.catalog.import_obj for a QTable directly (see footprints implementation)
        if isinstance(catalog, str):
            self.catalog.import_file(catalog)
        else:  # pragma: no cover
            raise ValueError("catalog must be a string (file path)")

    def vue_do_search(self, *args, **kwargs):
        # calls self.search() which handles all of the searching logic
        self.search()

    def clear(self, hide_only=True):
        # gets the current viewer
        viewer = self.viewer.selected_obj

        if not hide_only and self._marker_name in self.app.data_collection.labels:
            # resetting values
            self.results_available = False
            self.number_of_results = 0

            # all markers are removed from the viewer
            viewer.remove_markers(marker_name=self._marker_name)

        elif self.results_available:
            from jdaviz.utils import layer_is_table_data

            # resetting values
            self.results_available = False
            self.number_of_results = 0

            # markers still there, just hidden
            for lyr in viewer.layers:
                if layer_is_table_data(lyr.layer) and lyr.layer.label == self._marker_name:
                    lyr.visible = False

    def vue_do_clear(self, *args, **kwargs):
        self.clear()
