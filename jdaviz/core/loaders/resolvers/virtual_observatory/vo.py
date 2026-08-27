from astropy import units as u

from pyvo import registry
from pyvo.dal.exceptions import DALFormatError, DALQueryError
from pyvo.utils.vocabularies import VocabularyError
from requests.exceptions import ConnectionError as RequestConnectionError
from traitlets import Bool, Any, List, Unicode, observe

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
                "producttype", "search_input", "viewer", "coordframe",
                "radius", "radius_unit",
                "source",
                "catalog", "catalog_subset", "catalog_col_type", "catalog_name_col",
                "query_progress",
                "resource_filter_coverage", "waveband", "resource",
                "max_results",
                "query_archive"
            ],
        )

    @property
    def _query_archive_label(self):
        return self.resource_selected

    @staticmethod
    def _registry_search(*constraints):
        """
        Search the VO registry for resources matching ``constraints``.

        Split out from `query_registry_resources` to mirror `_query_single_coord`.
        Doing so also allows for easier testing.
        """
        return registry.search(*constraints)

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
            self._query_message(error_msg, color="error",
                                traceback=ValueError(error_msg), raise_msg=True)

        # Clear existing resources list and any messages
        self._clear_query_messages()
        self.resource.choices = []
        self.resource_selected = ""

        # Resolve the coordinate used for coverage filtering before querying the
        # registry.
        coord = None
        if self.resource_filter_coverage:
            coord = self._source_to_skycoord(add_query_message=False)
            if coord is None:
                error_msg = f"Unable to resolve source coordinates: {self.source}"
                self._query_message(error_msg, color="error",
                                    traceback=LookupError(error_msg), raise_msg=True)

        try:
            registry_args = [
                registry.Servicetype(VO_PROTOCOL[self.producttype_selected]['protocol']),
                registry.Waveband(self.waveband_selected),
            ]
            if self.resource_filter_coverage:
                # noinspection bad-argument-type
                registry_args.append(
                    registry.Spatial(
                        (coord, (self.radius * u.Unit(self.radius_unit.selected))),
                        intersect="overlaps",
                    )
                )
            self._full_registry_results = self._registry_search(*registry_args)
            self.resource.choices = list(
                self._full_registry_results.getcolumn("short_name")
            )
            if not self.resource.choices:
                # otherwise the (empty) dropdown is the only indication of the outcome
                # TODO: no choices should also trigger the invalid 'This field is required'
                #  message beneath the dropdown but it doesn't happen until you try to make
                #  a selection on nothing.
                msg = f"No {self.waveband_selected} {self.producttype_selected.lower()} "\
                      "resources found in the VO registry"
                if self.resource_filter_coverage:
                    msg += (f" for source: {self.source}. "
                            f"Try a different waveband or product type, "
                            f"or disable coverage filtering.")
                else:
                    msg += ". Try a different waveband or product type."

                self._query_message(msg, color='warning')

        except (DALFormatError, VocabularyError) as e:
            # HTTP Error 403 is being issued as a string as part of the
            # VocabularyError when the registry is having issues.
            # NOTE: VocabularyError does not carry a ``cause``.
            cause = getattr(e, 'cause', None)
            if type(cause) is RequestConnectionError or 'HTTP Error 403' in str(e):
                self._query_message(
                    f"Can't connect to VO registry. Check your internet connection: {e}",
                    color="error", traceback=e, raise_msg=True
                )
            else:
                self._query_message(f"An error occurred querying the VO Registry: {e}",
                                    color="error", traceback=e, raise_msg=True)
        except Exception as e:
            self._query_message(f"An error occurred querying the VO Registry: {e}",
                                color="error", traceback=e, raise_msg=True)

    def _query_single_coord(self, skycoord_center):
        """
        Query the selected VO resource for a single ``SkyCoord`` center.

        Returns an astropy Table (or None if the resource returned no results).
        """
        vo_service = self._full_registry_results[
            self.resource_selected
        ].get_service(service_type=VO_PROTOCOL[self.producttype_selected]['protocol'])
        # search service using these coords.
        try:
            vo_results = vo_service.search(
                skycoord_center,
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
            if "Wrong FORMAT=image/fits,image/fits" not in str(e):
                # any other query failure is reported by _query_single_coord_reporting
                raise
            vo_results = vo_service.search(
                skycoord_center,
                **{
                    "diameter" if self.producttype_selected == "Spectrum" else "size": (
                        (self.radius * u.Unit(self.radius_unit.selected))
                        if self.radius > 0.0
                        else None
                    )
                },
            )

        if len(vo_results) == 0:
            return None
        return vo_results.to_table()
