from astropy.coordinates import SkyCoord
from astropy import units as u

from pyvo.utils import vocabularies  # noqa: F401
from pyvo import registry
from pyvo.dal.exceptions import DALFormatError, DALQueryError
from requests.exceptions import ConnectionError as RequestConnectionError
from traitlets import Bool, Any, List, observe

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import loader_resolver_registry
from jdaviz.core.template_mixin import (
    SelectPluginComponent,
    with_spinner,
)
from jdaviz.core.loaders.resolvers import BaseConeSearchResolver
from jdaviz.core.user_api import LoaderUserApi

__all__ = ["VOResolver"]


@loader_resolver_registry("virtual observatory")
class VOResolver(BaseConeSearchResolver):
    template_file = __file__, "vo.vue"

    waveband_items = List().tag(sync=True)
    waveband_selected = Any().tag(sync=True)  # Any to accept Nonetype
    resource_filter_coverage = Bool(False).tag(sync=True)
    resource_items = List([]).tag(sync=True)
    resource_selected = Any().tag(sync=True)  # Any to accept Nonetype
    resources_loading = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Waveband properties to filter available registry resources
        self.waveband = SelectPluginComponent(
            self, items="waveband_items", selected="waveband_selected"
        )

        self.waveband.choices = (
            w.lower() for w in vocabularies.get_vocabulary("messenger")["terms"]
        )

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
                "viewer", "coordframe", "radius", "radius_unit",
                "source",
                "resource_filter_coverage", "waveband", "resource",
                "query_archive"
            ],
        )

    @observe("waveband_selected",
             "source", "coordframe_selected",
             "radius", "radius_unit_selected",
             "resource_filter_coverage")
    @with_spinner(spinner_traitlet="resources_loading")
    def query_registry_resources(self, event={}):
        """
        Query Virtual Observatory registry for all SIA services
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
                    if self.viewer == "Manual"
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
                registry.Servicetype("sia"),
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
        except DALFormatError as e:
            if type(e.cause) is RequestConnectionError:
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

    @with_spinner(spinner_traitlet="results_loading")
    def query_archive(self):
        """
        Once a specific VO resource is selected, query it with the user-specified source target.
        User input for source is first attempted to be parsed as a SkyCoord coordinate. If not,
        then attempts to parse as a target name.
        """
        try:
            # Query SIA service
            # Service is indexed via short name (resource_selected), which is the suggested way
            # according to PyVO docs. Though disclaimer that collisions COULD occur. If so,
            # consider indexing on the full IVOID, which is guaranteed unique.
            sia_service = self._full_registry_results[
                self.resource_selected
            ].get_service(service_type="sia")
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
            # Once coordinate lookup is complete, search service using these coords.
            try:
                sia_results = sia_service.search(
                    coord,
                    size=(
                        (self.radius * u.Unit(self.radius_unit.selected))
                        if self.radius > 0.0
                        else None
                    ),
                    format="image/fits",
                )
            except DALQueryError as e:
                # We've run into issues where the service assumes a FORMAT and injects it for us.
                # If the "image/fits" is duplicated, remove our requested format and rely on theirs
                if "Wrong FORMAT=image/fits,image/fits" in str(e):
                    sia_results = sia_service.search(
                        coord,
                        size=(
                            (self.radius * u.Unit(self.radius_unit.selected))
                            if self.radius > 0.0
                            else None
                        ),
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
            if len(sia_results) == 0:
                self.hub.broadcast(
                    SnackbarMessage(
                        f"No observations returned at coords {coord} from VO SIA resource: {sia_service.baseurl}",  # noqa: E501
                        sender=self,
                        color="error",
                    )
                )
            else:
                self.hub.broadcast(
                    SnackbarMessage(
                        f"{len(sia_results)} SIA results found!",
                        sender=self,
                        color="success",
                    )
                )
        except Exception as e:
            self.hub.broadcast(
                SnackbarMessage(
                    f"Unable to locate files for source {self.source}: {e}",
                    sender=self,
                    color="error",
                    traceback=e
                )
            )
        try:
            self._output = sia_results.to_table()
        except Exception as e:
            self.hub.broadcast(
                SnackbarMessage(
                    f"Unable to populate table for source {self.source}: {e}",
                    sender=self,
                    color="error",
                    traceback=e
                )
            )
        self._resolver_input_updated()

    def vue_query_archive(self, _=None):
        self.query_archive()

    def parse_input(self):
        return self._output
