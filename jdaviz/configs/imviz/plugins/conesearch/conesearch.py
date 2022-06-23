from astropy.table import Table
from astropy.coordinates import SkyCoord
from astroquery.sdss import SDSS

from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, ViewerSelectMixin

__all__ = ['ConeSearch']


@tray_registry('imviz-conesearch', label="Imviz ConeSearch")
class ConeSearch(PluginTemplateMixin, ViewerSelectMixin):
    template_file = __file__, "conesearch.vue"

    def __init__(self, *args, **kwargs):
        self.init_astrowidgets_api()
        super().__init__(*args, **kwargs)

    def vue_do_conesearch(self, *args, **kwargs):
        query_region_result = SDSS.query_region(SkyCoord('00h07m13.8036s +14d56m16.8706s', frame='icrs'), radius='0.015 deg', data_release=17)

        skycoord_table = SkyCoord(query_region_result['ra'], query_region_result['dec'], unit='deg')

        conesearch_results = Table({'coord': [skycoord_table]})
        self.add_markers(table=conesearch_results, use_skycoord=True, marker_name='conesearch_results')


        # get top layer of viewer, zoom limits, work radius from that, convert that to the query
        # the radius should just be the corner of the image (right now just get some radius and center hardcoded)
        # get the data outputted?
