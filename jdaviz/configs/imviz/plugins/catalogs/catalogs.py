import numpy as np
import numpy.ma as ma

from traitlets import List, Unicode, Bool, Int

from astropy.table import QTable
from astropy.coordinates import SkyCoord
from astroquery.sdss import SDSS

from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, ViewerSelectMixin

__all__ = ['Catalogs']


@tray_registry('imviz-catalogs', label="Catalog Search")
class Catalogs(PluginTemplateMixin, ViewerSelectMixin):
    template_file = __file__, "catalogs.vue"
    catalog_items = List([]).tag(sync=True)
    catalog_selected = Unicode("").tag(sync=True)
    results_available = Bool(False).tag(sync=True)
    number_of_results = Int(0).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # TODO: Add more catalogs.
        self.catalog_items = ["SDSS"]

        if self.catalog_selected not in self.catalog_items:
            self.catalog_selected = self.catalog_items[0]

    def search(self):
        # calling clear in the case the user forgot after searching
        self.vue_do_clear()

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
            # queries the region (based on the provided center point and radius)
            # finds all the sources in that region
            query_region_result = SDSS.query_region(skycoord_center, radius=zoom_radius,
                                                    data_release=17)
            # TODO: Filter this table the same way as the actual displayed markers.
            # attach the table to the app for Python extraction
            self.app._catalog_source_table = query_region_result
            self.results_available = True

        else:
            self.results_available = False
            self.number_of_results = 0
            raise NotImplementedError(f"{self.catalog_selected} not a supported catalog")

        # nothing happens in the case the query returned empty
        if query_region_result is None:
            self.number_of_results = 0
            return

        # TODO: Column names are catalog-dependent. Need to consider this when adding new catalogs.
        # a table is created storing the 'ra' and 'dec' plottable points of each source found
        skycoord_table = SkyCoord(query_region_result['ra'], query_region_result['dec'], unit='deg')

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
        viewer.add_markers(table=catalog_results, use_skycoord=True, marker_name='catalog_results')

    def vue_do_search(self, *args, **kwargs):
        # calls self.search() which handles all of the searching logic
        self.search()

    def vue_do_clear(self, *args, **kwargs):

        if self.results_available:
            # resetting values
            self.results_available = False
            self.number_of_results = 0
            # gets the current viewer
            viewer = self.viewer.selected_obj

            # all markers are removed from the viewer
            viewer.reset_markers()
