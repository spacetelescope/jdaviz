import numpy as np
import numpy.ma as ma

from traitlets import List, Unicode, Bool, Int, observe

from astropy.table import QTable
from astropy.coordinates import SkyCoord
from astroquery.sdss import SDSS

from jdaviz.core.events import ViewerAddedMessage, ViewerRemovedMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, ViewerSelectMixin

__all__ = ['Catalogs']


@tray_registry('imviz-catalogs', label="Imviz Catalogs")
class Catalogs(PluginTemplateMixin, ViewerSelectMixin):
    template_file = __file__, "catalogs.vue"
    viewer_items = List([]).tag(sync=True)
    selected_viewer = Unicode("").tag(sync=True)
    results_available = Bool(False).tag(sync=True)
    number_of_results = Int(0).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._default_viewer = f'{self.app.config}-0'

        self.hub.subscribe(self, ViewerAddedMessage, handler=self._on_viewers_changed)
        self.hub.subscribe(self, ViewerRemovedMessage, handler=self._on_viewers_changed)

        self._on_viewers_changed()  # Populate it on start-up

    def _on_viewers_changed(self, msg=None):
        self.viewer_items = self.app.get_viewer_ids()

        # Selected viewer was removed but Imviz always has a default viewer to fall back on.
        if self.selected_viewer not in self.viewer_items:
            self.selected_viewer = self._default_viewer

    @observe("selected_viewer")
    def vue_do_catalogs(self, *args, **kwargs):
        # no querying occurs while the plugin has not been opened
        if not self.plugin_opened:
            return

        # gets the current viewer
        viewer = self.app.get_viewer_by_id(self.selected_viewer)

        # nothing happens in the case there is no image in the viewer
        if viewer.state.reference_data is None:
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

        # radius for querying the region is based on the distance between the longest zoom limits and the center point
        zoom_radius = max(skycoord_center.separation(zoom_coordinate))

        # queries the region (based on the provided center point and radius) to find all the sources in that region
        query_region_result = SDSS.query_region(skycoord_center, radius=zoom_radius, data_release=17)
        self.results_available = True
        # nothing happens in the case the query returned empty
        if query_region_result is None:
            self.number_of_results = 0
            return

        # a table is created storing the 'ra' and 'dec' plottable points of each source found
        skycoord_table = SkyCoord(query_region_result['ra'], query_region_result['dec'], unit='deg')

        # coordinates found are converted to pixel coordinates
        pixel_table = viewer.state.reference_data.coords.world_to_pixel(skycoord_table)
        # coordinates are filtered out (using a mask) if outside the zoom range
        pair_pixel_table = np.dstack((pixel_table[0], pixel_table[1]))
        masked_table = ma.masked_outside(pair_pixel_table, [zoom_x_min, zoom_y_min], [zoom_x_max, zoom_y_max])
        filtered_table = ma.compress_rows(masked_table[0])
        # coordinates are split into their respective x and y values and then converted to sky coordinates
        filtered_pair_pixel_table = np.array(np.hsplit(filtered_table, 2))
        x_coordinates = np.squeeze(filtered_pair_pixel_table[0])
        y_coordinates = np.squeeze(filtered_pair_pixel_table[1])
        filtered_skycoord_table = viewer.state.reference_data.coords.pixel_to_world(x_coordinates, y_coordinates)

        # QTable stores all the filtered sky coordinate points to be marked
        catalog_results = QTable({'coord': filtered_skycoord_table})
        self.number_of_results = len(catalog_results)

        # markers are added to the viewer based on the table
        viewer.marker = {'color': 'red', 'alpha': 0.8, 'markersize': 5, 'fill': False}
        viewer.add_markers(table=catalog_results, use_skycoord=True, marker_name='catalog_results')

    @observe("selected_viewer")
    def vue_do_clear(self, *args, **kwargs):
        # no querying occurs while the plugin has not been opened
        if not self.plugin_opened:
            return

        self.results_available = False
        # gets the current viewer
        viewer = self.app.get_viewer_by_id(self.selected_viewer)

        # all markers are removed from the viewer
        viewer.reset_markers()
