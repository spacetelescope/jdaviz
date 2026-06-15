from astropy.coordinates import SkyCoord
from astropy.coordinates.name_resolve import NameResolveError
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

        # Get list of available telescopes, filtering out disabled ones
        self.can_filter_science = True
        all_telescopes = ['JWST', 'HST', 'SDSS', 'Gaia']
        disabled_telescopes = self.app.state.settings.get('disabled_astroquery_telescopes', [])
        available_telescopes = [t for t in all_telescopes if t not in disabled_telescopes]

        self.telescope = SelectPluginComponent(
            self, items="telescope_items", selected="telescope_selected",
            manual_options=available_telescopes
        )

        # Listen for changes to app.state.settings
        self.app.state.add_callback('settings', self._on_app_settings_changed)

    def _on_app_settings_changed(self, new_settings_dict):
        """
        Update telescope options when settings change.
        """
        # Call parent's method to handle server_is_remote and other settings
        super()._on_app_settings_changed(new_settings_dict)

        # Recalculate available telescopes based on new settings
        all_telescopes = ['JWST', 'HST', 'SDSS', 'Gaia']
        disabled_telescopes = new_settings_dict.get('disabled_astroquery_telescopes', [])
        available_telescopes = [t for t in all_telescopes if t not in disabled_telescopes]

        # Update the manual options and refresh items
        if self.telescope._manual_options != available_telescopes:
            self.telescope._manual_options = available_telescopes
            # Directly update the items list to ensure sync
            manual_options_dicts = [self.telescope._to_item(opt) for opt in available_telescopes]
            self.telescope.items = manual_options_dicts
            # Reset selection if current selection is no longer valid
            if self.telescope_selected and self.telescope_selected not in available_telescopes:
                if len(available_telescopes) > 0:
                    self.telescope_selected = available_telescopes[0]
                else:
                    self.telescope_selected = ''

    @property
    def user_api(self):
        return LoaderUserApi(
            self,
            expose=[
                "input_select", "viewer", "coordframe", "radius", "radius_unit",
                "source",
                "catalog", "catalog_subset", "catalog_col_type",
                "query_progress",
                "telescope",
                "max_results",
                "query_archive",
                "limit_to_science_products"
            ],
        )

    def _source_to_skycoord(self):
        # Check to see if source is "[RA] [Dec]" (in degrees)
        split_source = self.source.split(' ')
        if len(split_source) == 2:
            try:
                return SkyCoord(self.source, unit=u.deg, frame=self.coordframe.selected)
            except ValueError:
                pass

        # Otherwise try to resolve coordinates from the source name
        try:
            return SkyCoord.from_name(self.source, frame=self.coordframe.selected)
        except NameResolveError as e:
            # Sesame name resolution can fail when the service is unreachable (SSL timeout,
            # redirect error, etc.). Surface the failure as a snackbar rather than propagating
            # the exception to the caller. Keep processing below so we clear stale results.
            errmsg = f"Unable to resolve source coordinates: {self.source}"
            self.hub.broadcast(SnackbarMessage(errmsg, color='error', sender=self, traceback=e))
            return None


    def _query_single_coord(self, skycoord_center):
        """
        Query the selected archive for a single SkyCoord.
        Returns an astropy Table or None.
        """
        output = None
        radius = self.radius * u.Unit(self.radius_unit.selected)

        if self.telescope.selected in ('JWST', 'HST'):
            from astroquery.mast import MastMissions

            mission = MastMissions(mission=self.telescope.selected)
            output = mission.query_region(skycoord_center, radius=radius.value)

        elif self.telescope.selected == 'SDSS':
            from astroquery.sdss import SDSS

            r_max = 3 * u.arcmin
            if radius > r_max:
                self.hub.broadcast(SnackbarMessage(
                    f"Radius for {self.telescope.selected} has max radius of {r_max}\' but got "
                    f"{radius.to(u.arcmin)}, using {r_max}.",
                    color='warning', sender=self))
                radius = r_max

            try:
                output = SDSS.query_region(skycoord_center, radius=radius,
                                           data_release=17)
            except Exception as e:  # nosec
                errmsg = (f"Failed to query {self.telescope.selected} with "
                          f"c={skycoord_center} and r={radius}: {repr(e)}")
                self.hub.broadcast(SnackbarMessage(errmsg, color='error',
                                                   sender=self,
                                                   traceback=e))
                output = None

        elif self.telescope.selected == 'Gaia':
            from astroquery.gaia import Gaia

            Gaia.ROW_LIMIT = self.max_results
            output = Gaia.query_object(skycoord_center, radius=radius)

        elif skycoord_center is not None:
            raise NotImplementedError(
                f"Querying for {self.telescope.selected} is not supported."
            )

        return output

    @with_spinner(spinner_traitlet="results_loading")
    def query_archive(self):
        # --- Catalog mode: loop over catalog rows ---
        if self.input_selected == 'Catalog':
            self._query_catalog(self._query_single_coord)
            return

        # --- Source / Viewer mode: single coordinate ---
        output = None
        skycoord_center = None

        try:
            skycoord_center = self._source_to_skycoord()
        except NameResolveError as e:
            errmsg = f"Unable to resolve source coordinates: {self.source}"
            self.hub.broadcast(SnackbarMessage(errmsg, color='error', sender=self, traceback=e))

        if skycoord_center is not None:
            output = self._query_single_coord(skycoord_center)

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
