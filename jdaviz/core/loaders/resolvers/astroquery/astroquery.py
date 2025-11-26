from astropy.coordinates import SkyCoord
from astropy import units as u


from traitlets import Unicode, List

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import loader_resolver_registry
from jdaviz.core.template_mixin import (
    SelectPluginComponent,
    with_spinner,
)
from jdaviz.core.loaders.resolvers import BaseConeSearchResolver
from jdaviz.core.user_api import LoaderUserApi

__all__ = ["AstroqueryResolver"]


@loader_resolver_registry("astroquery")
class AstroqueryResolver(BaseConeSearchResolver):
    template_file = __file__, "astroquery.vue"

    telescope_items = List([]).tag(sync=True)
    telescope_selected = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.telescope = SelectPluginComponent(
            self, items="telescope_items", selected="telescope_selected",
            manual_options=['SDSS', 'Gaia']
        )

    @property
    def user_api(self):
        return LoaderUserApi(
            self,
            expose=[
                "viewer", "coordframe", "radius", "radius_unit",
                "source",
                "telescope",
                "max_results",
                "query_archive"
            ],
        )

    @with_spinner(spinner_traitlet="results_loading")
    def query_archive(self):
        skycoord_center = SkyCoord.from_name(self.source, frame=self.coordframe.selected)
        radius = self.radius * u.Unit(self.radius_unit.selected)

        if self.telescope.selected == 'SDSS':
            from astroquery.sdss import SDSS

            r_max = 3 * u.arcmin
            if radius > r_max:  # SDSS now has radius max limit
                self.hub.broadcast(SnackbarMessage(
                    f"Radius for {self.telescope.selected} has max radius of {r_max}\' but got "
                    f"{radius.to(u.arcmin)}, using {r_max}.",
                    color='warning', sender=self))
                radius = r_max

            # queries the region (based on the provided center point and radius)
            # finds all the sources in that region
            try:
                output = SDSS.query_region(skycoord_center, radius=radius,
                                           data_release=17)
            except Exception as e:  # nosec
                errmsg = (f"Failed to query {self.telescope.selected} with c={skycoord_center} and "
                          f"r={radius}: {repr(e)}")
                self.hub.broadcast(SnackbarMessage(errmsg, color='error',
                                                   sender=self,
                                                   traceback=e))
                output = None  # will force returned_max_results = False, returned_no_results = True
        elif self.telescope.selected == 'Gaia':
            from astroquery.gaia import Gaia

            Gaia.ROW_LIMIT = self.max_results
            output = Gaia.query_object(skycoord_center, radius=radius)
        else:
            raise NotImplementedError(f"Querying for {self.telescope.selected} is not supported.")

        if output is not None and len(output) > self.max_results:
            output = output[:self.max_results]
            self.returned_max_results = True
        else:
            self.returned_max_results = False
        if output is None or len(output) == 0:
            self.returned_no_results = True
        else:
            self.returned_no_results = False
        self._output = output

        self._resolver_input_updated()

    def vue_query_archive(self, _=None):
        self.query_archive()

    def parse_input(self):
        return self._output
