import os

import numpy as np
import numpy.ma as ma
from astropy import units as u
from astropy.table import QTable
from astropy.coordinates import SkyCoord
from traitlets import List, Unicode, Bool, Int, observe

from jdaviz.configs.default.plugins.data_tools.file_chooser import FileChooser
from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin, ViewerSelectMixin,
                                        SelectPluginComponent)

__all__ = ['Catalogs']


@tray_registry('imviz-catalogs', label="Catalog Search")
class Catalogs(PluginTemplateMixin, ViewerSelectMixin):
    """
    See the :ref:`Catalog Search Plugin Documentation <imviz-catalogs>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    """
    template_file = __file__, "catalogs.vue"
    catalog_items = List([]).tag(sync=True)
    catalog_selected = Unicode("").tag(sync=True)
    from_file = Unicode().tag(sync=True)
    from_file_message = Unicode().tag(sync=True)
    results_available = Bool(False).tag(sync=True)
    number_of_results = Int(0).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.catalog = SelectPluginComponent(self,
                                             items='catalog_items',
                                             selected='catalog_selected',
                                             manual_options=['SDSS', 'From File...'])

        # file chooser for From File
        start_path = os.environ.get('JDAVIZ_START_DIR', os.path.curdir)
        self._file_upload = FileChooser(start_path)
        self.components = {'g-file-import': self._file_upload}
        self._file_upload.observe(self._on_file_path_changed, names='file_path')
        self._cached_table_from_file = {}
        self._marker_name = 'catalog_results'

    def _on_file_path_changed(self, event):
        self.from_file_message = 'Checking if file is valid'
        path = event['new']
        if (path is not None
                and not os.path.exists(path)
                or not os.path.isfile(path)):
            self.from_file_message = 'File path does not exist'
            return

        try:
            table = QTable.read(path)
        except Exception:
            self.from_file_message = 'Could not parse file with astropy.table.QTable.read'
            return

        if 'sky_centroid' not in table.colnames:
            self.from_file_message = 'Table does not contain required sky_centroid column'
            return

        # since we loaded the file already to check if its valid, we might as well cache the table
        # so we don't have to re-load it when clicking search.  We'll only keep the latest entry
        # though, but store in a dict so we can catch if the file path was changed from the API
        self._cached_table_from_file = {path: table}
        self.from_file_message = ''

    @observe('from_file')
    def _from_file_changed(self, event):
        if len(event['new']):
            if not os.path.exists(event['new']):
                raise ValueError(f"{event['new']} does not exist")
            self.catalog.selected = 'From File...'
        else:
            # NOTE: select_default will change the value even if the current value is valid
            # (so will change from 'From File...' to the first entry in the dropdown)
            self.catalog.select_default()

    def vue_set_file_from_dialog(self, *args, **kwargs):
        self.from_file = self._file_upload.file_path

    def search(self):
        """
        Search the catalog, display markers on the viewer, and return a table of results (or None
        if no results available)
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
                self.hub.broadcast(SnackbarMessage(
                    f"Failed to query {self.catalog_selected} with c={skycoord_center} and "
                    f"r={zoom_radius}: {repr(e)}", color='error', sender=self))
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

        elif self.catalog_selected == 'From File...':
            # all exceptions when going through the UI should have prevented setting this path
            # but this exceptions might be raised here if setting from_file from the UI
            table = self._cached_table_from_file.get(self.from_file, QTable.read(self.from_file))
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
        filtered_skycoord_table = viewer.state.reference_data.coords.pixel_to_world(x_coordinates,
                                                                                    y_coordinates)

        # QTable stores all the filtered sky coordinate points to be marked
        catalog_results = QTable({'coord': filtered_skycoord_table})
        self.number_of_results = len(catalog_results)

        # markers are added to the viewer based on the table
        viewer.marker = {'color': 'red', 'alpha': 0.8, 'markersize': 5, 'fill': False}
        viewer.add_markers(table=catalog_results, use_skycoord=True, marker_name=self._marker_name)

        return skycoord_table

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
            from jdaviz.configs.imviz.helper import layer_is_table_data

            # resetting values
            self.results_available = False
            self.number_of_results = 0

            # markers still there, just hidden
            for lyr in viewer.layers:
                if layer_is_table_data(lyr.layer) and lyr.layer.label == self._marker_name:
                    lyr.visible = False

    def vue_do_clear(self, *args, **kwargs):
        self.clear()
