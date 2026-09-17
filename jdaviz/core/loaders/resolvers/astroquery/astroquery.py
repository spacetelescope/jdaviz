from astropy import units as u


from traitlets import Unicode, List

from jdaviz.core.registries import loader_resolver_registry
from jdaviz.core.template_mixin import (
    SelectPluginComponent,
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
                "search_input", "viewer", "coordframe", "radius", "radius_unit",
                "source",
                "catalog", "catalog_subset", "catalog_col_type", "catalog_name_col",
                "query_progress",
                "telescope",
                "max_results",
                "query_archive",
                "limit_to_science_products"
            ],
        )

    @property
    def _query_archive_label(self):
        return self.telescope.selected

    def _query_single_coord(self, skycoord_center):
        """
        Query the selected archive for a single ``SkyCoord`` center.

        Returns an astropy Table (or None on failure / unsupported telescope).
        """
        radius = self.radius * u.Unit(self.radius_unit.selected)

        if self.telescope.selected in ('JWST', 'HST'):
            from astroquery.mast import MastMissions

            mission = MastMissions(mission=self.telescope.selected)
            output = mission.query_region(skycoord_center, radius=radius.value)

        elif self.telescope.selected == 'SDSS':
            from astroquery.sdss import SDSS

            r_max = 3 * u.arcmin
            if radius > r_max:  # SDSS now has radius max limit
                self._query_message(
                    f"Radius for {self.telescope.selected} has max radius of {r_max}\' but got "
                    f"{radius.to(u.arcmin)}, using {r_max}.",
                    color='warning', raise_msg=True)
                radius = r_max

            # queries the region (based on the provided center point and radius)
            # finds all the sources in that region
            output = SDSS.query_region(skycoord_center, radius=radius,
                                       data_release=17)

        elif self.telescope.selected == 'Gaia':
            from astroquery.gaia import Gaia

            Gaia.ROW_LIMIT = self.max_results
            output = Gaia.query_object(skycoord_center, radius=radius)
        else:
            # this can only occur in the API and therefore doesn't need to go through
            # _query_message
            raise NotImplementedError(f"Querying for {self.telescope.selected} is not supported.")

        return output
