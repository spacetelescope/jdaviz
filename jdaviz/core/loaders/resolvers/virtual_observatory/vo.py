from astropy.coordinates import SkyCoord
from astropy import units as u

from pyvo import registry
from pyvo.dal.exceptions import DALFormatError, DALQueryError
from pyvo.utils.vocabularies import VocabularyError
from requests.exceptions import ConnectionError as RequestConnectionError
from traitlets import Bool, Any, List, Unicode, observe

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import loader_resolver_registry
from jdaviz.core.template_mixin import (
    SelectPluginComponent,
    with_spinner,
)
from jdaviz.core.loaders.resolvers import BaseConeSearchResolver
from jdaviz.core.user_api import LoaderUserApi


__all__ = ["VOResolver"]

VO_PROTOCOL = {"Image": {'protocol': 'sia', 'size_arg': 'size'},
               "Spectrum": {'protocol': 'ssa', 'size_arg': 'diameter'},
               "Catalog": {'protocol': 'scs', 'size_arg': 'radius'}}


@loader_resolver_registry("virtual observatory")
class VOResolver(BaseConeSearchResolver):
    template_file = __file__, "vo.vue"

    producttype_selected = Unicode("Image").tag(sync=True)
    producttype_choices = List(list({"label": type} for type in VO_PROTOCOL.keys())).tag(sync=True)

    waveband_items = List().tag(sync=True)
    waveband_selected = Any().tag(sync=True)  # Any to accept Nonetype
    resource_filter_coverage = Bool(False).tag(sync=True)
    resource_items = List([]).tag(sync=True)
    resource_selected = Any().tag(sync=True)  # Any to accept Nonetype
    resources_loading = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.producttype = SelectPluginComponent(
            self, items="producttype_choices", selected="producttype_selected"
        )

        # Waveband properties to filter available registry resources
        self.waveband = SelectPluginComponent(
            self, items="waveband_items", selected="waveband_selected"
        )

        # How often are we really discovering a new astronomical messenger?
        # I think we can hard code this.
        self.waveband.choices = ['photon', 'radio', 'millimeter', 'infrared', 'optical',
                                 'uv', 'euv', 'x-ray', 'gamma-ray', 'neutrino']

        self.waveband_selected = ""

        self._full_registry_results = None
        self.resource_selected = ""
        self.resource = SelectPluginComponent(
            self, items="resource_items", selected="resource_selected"
        )
        self.resource.choices = []

    @property
    def user_api(self):
        return LoaderUserApi(
            self,
            expose=[
                "producttype", "search_input_select", "viewer", "coordframe",
                "radius", "radius_unit",
                "source",
                "catalog", "catalog_subset", "catalog_col_type", "catalog_name_col",
                "query_progress",
                "resource_filter_coverage", "waveband", "resource",
                "query_archive"
            ],
        )

    @observe("producttype_selected", "waveband_selected",
             "source", "coordframe_selected",
             "radius", "radius_unit_selected",
             "resource_filter_coverage")
    @with_spinner(spinner_traitlet="resources_loading")
    def query_registry_resources(self, event={}):
        """
        Query Virtual Observatory registry for all services
        that serve data in that waveband around the source.
        Then update the dropdown accordingly.
        """
        # If waveband was changed to nothing, immediately quit
        # Don't throw an error due to trigger by plugin init
        if not self.waveband_selected:
            return

        # No need to update if the change was from source but coverage filtering is off
        if (event.get("name") in ("source", "coordframe_selected", "radius", "radius_unit_selected")
                and not self.resource_filter_coverage):
            return

        # Can't filter by coverage if we don't have a source to filter on
        if self.resource_filter_coverage and not self.source:
            error_msg = (
                "Source is required for registry querying when coverage filtering is enabled. "
                + (
                    "Please enter your coordinates above "
                    if self.search_input_selected != 'Viewer'
                    else f"Load data into viewer {self.viewer} first before querying "
                )
                + "or disable coverage filtering."
            )
            self.hub.broadcast(SnackbarMessage(error_msg, sender=self, color="error"))
            raise ValueError(error_msg)

        # Clear existing resources list
        self.resource.choices = []
        self.resource_selected = ""

        try:
            registry_args = [
                registry.Servicetype(VO_PROTOCOL[self.producttype_selected]['protocol']),
                registry.Waveband(self.waveband_selected),
            ]
            # If coverage filtering is enabled, lookup current
            # source coordinate and add a Spatial search constraint
            if self.resource_filter_coverage:
                try:
                    # First parse user-provided source as direct coordinates
                    coord = SkyCoord(
                        self.source, unit=u.deg, frame=self.coordframe_selected
                    )
                except Exception:
                    try:
                        # If that didn't work, try parsing it as an object name
                        coord = SkyCoord.from_name(
                            self.source, frame=self.coordframe_selected
                        )
                    except Exception as e:
                        self.hub.broadcast(
                            SnackbarMessage(
                                f"Unable to resolve source coordinates: {self.source}",
                                sender=self,
                                color="error",
                                traceback=e
                            )
                        )
                        raise LookupError(
                            f"Unable to resolve source coordinates: {self.source}"
                        )
                registry_args.append(
                    registry.Spatial(
                        (coord, (self.radius * u.Unit(self.radius_unit.selected))),
                        intersect="overlaps",
                    )
                )
            self._full_registry_results = registry.search(*registry_args)
            self.resource.choices = list(
                self._full_registry_results.getcolumn("short_name")
            )
        except (DALFormatError, VocabularyError) as e:
            # HTTP Error 403 is being issued as a string as part of the
            # VocabularyError when the registry is having issues.
            if type(e.cause) is RequestConnectionError or 'HTTP Error 403' in str(e):
                self.hub.broadcast(
                    SnackbarMessage(
                        f"Can't connect to VO registry. Check your internet connection: {e}",
                        sender=self,
                        color="error",
                        traceback=e
                    )
                )
            else:
                raise e
        except Exception as e:
            self.hub.broadcast(
                SnackbarMessage(
                    f"An error occured querying the VO Registry: {e}",
                    sender=self,
                    color="error",
                    traceback=e
                )
            )
            raise

    def _source_to_skycoord(self):
        """
        Resolve ``self.source`` into a ``SkyCoord``. First attempts to parse as
        direct coordinates, then falls back to name resolution.
        Returns None (and broadcasts a snackbar) if resolution fails.
        """
        try:
            return SkyCoord(self.source, unit=u.deg, frame=self.coordframe_selected)
        except Exception:
            try:
                return SkyCoord.from_name(self.source, frame=self.coordframe_selected)
            except Exception as e:
                self.hub.broadcast(
                    SnackbarMessage(
                        f"Unable to resolve source coordinates: {self.source}",
                        sender=self,
                        color="error",
                        traceback=e
                    )
                )
                return None

    def _query_single_coord(self, coord):
        """
        Query the selected VO resource for a single ``SkyCoord`` center.

        Returns an astropy Table (or None on failure / no results).
        """
        try:
            vo_service = self._full_registry_results[
                self.resource_selected
            ].get_service(service_type=VO_PROTOCOL[self.producttype_selected]['protocol'])
            # search service using these coords.
            try:
                vo_results = vo_service.search(
                    coord,
                    **{
                        VO_PROTOCOL[self.producttype_selected]['size_arg']: (
                            (self.radius * u.Unit(self.radius_unit.selected))
                            if self.radius > 0.0
                            else None
                        )
                    },
                    format=("" if self.producttype_selected == "Catalog" else "fits"),
                )
            except DALQueryError as e:
                # We've run into issues where the service assumes a FORMAT and injects it for us.
                # If the "image/fits" is duplicated, remove our requested format and rely on theirs
                if "Wrong FORMAT=image/fits,image/fits" in str(e):
                    vo_results = vo_service.search(
                        coord,
                        **{
                            "diameter" if self.producttype_selected == "Spectrum" else "size": (
                                (self.radius * u.Unit(self.radius_unit.selected))
                                if self.radius > 0.0
                                else None
                            )
                        },
                    )
                else:
                    self.hub.broadcast(
                        SnackbarMessage(
                            f"Query failed: {e}",
                            sender=self,
                            traceback=e,
                            color="error",
                        )
                    )
                    return None
            if len(vo_results) == 0:
                self.hub.broadcast(
                    SnackbarMessage(
                        f"No observations returned at coords {coord} from VO resource: "
                        f"{vo_service.baseurl}",
                        sender=self,
                        color="error",
                    )
                )
                return None
            return vo_results.to_table()
        except Exception as e:
            self.hub.broadcast(
                SnackbarMessage(
                    f"Unable to locate files for source {self.source}: {e}",
                    sender=self,
                    color="error",
                    traceback=e
                )
            )
            return None

    @with_spinner(spinner_traitlet="results_loading")
    def query_archive(self):
        """
        Once a specific VO resource is selected, query it with the user-specified source target.
        User input for source is first attempted to be parsed as a SkyCoord coordinate. If not,
        then attempts to parse as a target name.

        In "Catalog" input mode, the selected resource is queried once per catalog
        row and the results are stacked (see ``_query_catalog``).
        """
        # Catalog mode: loop over all (selected) catalog rows and stack results.
        if self.search_input_selected == 'Catalog':
            self._query_catalog(self._query_single_coord)
            return

        # Source / Viewer mode: single coordinate.
        coord = self._source_to_skycoord()
        self._output = self._query_single_coord(coord) if coord is not None else []

        if self._output is not None and len(self._output) > 0:
            self.hub.broadcast(
                SnackbarMessage(
                    f"{len(self._output)} {self.producttype_selected} results found!",
                    sender=self,
                    color="success",
                )
            )
        self._resolver_input_updated()

    def vue_query_archive(self, _=None):
        self.query_archive()

    def parse_input(self):
        return self._output
