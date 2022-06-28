from astropy.table import Table
from astropy.coordinates import SkyCoord
from astroquery.sdss import SDSS

from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, ViewerSelectMixin
from jdaviz.configs.imviz.helper import get_top_layer_index

__all__ = ['Catalogs']


@tray_registry('imviz-catalogs', label="Imviz Catalogs")
class Catalogs(PluginTemplateMixin, ViewerSelectMixin):
    template_file = __file__, "catalogs.vue"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def vue_do_catalogs(self, *args, **kwargs):
        # current viewer object
        curr_viewer = self.viewer.selected_obj

        # used to obtain the current image visible in the viewer
        viewer = self.app.get_viewer_by_id(self.viewer_selected)
        i = get_top_layer_index(viewer)
        data = viewer.state.layers[i].layer

        # obtains the center point of the current image and converts the point into sky coordinates
        # note to self: need to add in logic to handle cases where curr_viewer.state.reference_data.coords is None
        x_center = (curr_viewer.state.x_min + curr_viewer.state.x_max) * 0.5
        y_center = (curr_viewer.state.y_min + curr_viewer.state.y_max) * 0.5
        skycoord_center = curr_viewer.state.reference_data.coords.pixel_to_world(x_center, y_center)

        # obtains the viewer's zoom limits (just one) based on the visible layer
        zoom_limits = curr_viewer._get_zoom_limits(data)
        zoom_x_limit = zoom_limits[0, 0]
        zoom_y_limit = zoom_limits[0, 1]
        zoom_coordinate = curr_viewer.state.reference_data.coords.pixel_to_world(zoom_x_limit, zoom_y_limit)

        # radius for querying the region is based on the distance between the zoom limit and the center point
        zoom_radius = skycoord_center.separation(zoom_coordinate)

        # queries the region (based on the provided center point and radius) to find all the sources in that region
        query_region_result = SDSS.query_region(skycoord_center, radius=zoom_radius, data_release=17)

        # a table is created storing the 'ra' and 'dec' plottable points of each source found
        skycoord_table = SkyCoord(query_region_result['ra'], query_region_result['dec'], unit='deg')
        catalog_results = Table({'coord': [skycoord_table]})

        # markers are added to the viewer based on the table
        curr_viewer.add_markers(table=catalog_results, use_skycoord=True, marker_name='conesearch_results')

        # get top layer of viewer, zoom limits, work radius from that, convert that to the query
        # the radius should just be the corner of the image
        # get the data outputted?
