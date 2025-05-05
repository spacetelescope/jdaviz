from astropy.coordinates.builtin_frames import __all__ as all_astropy_frames
from astropy.coordinates import SkyCoord
from astropy import units as u

from pyvo.utils import vocabularies
from pyvo import registry
from pyvo.dal.exceptions import DALFormatError, DALQueryError
from requests.exceptions import ConnectionError as RequestConnectionError
from traitlets import Bool, Unicode, Any, List, Float, observe

from jdaviz.core.events import (
    SnackbarMessage,
    AddDataMessage,
    RemoveDataMessage,
    LinkUpdatedMessage,
)
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (
    PluginTemplateMixin,
    AddResultsMixin,
    TableMixin,
    ViewerSelect,
    SelectPluginComponent,
    UnitSelectPluginComponent,
    with_spinner,
)

__all__ = ["VoPlugin"]
vo_plugin_label = "Virtual Observatory"


@tray_registry("VoPlugin", label=vo_plugin_label)
class VoPlugin(PluginTemplateMixin, AddResultsMixin, TableMixin):
    """Plugin to query the Virtual Observatory and load data into Imviz"""

    template_file = __file__, "vo_plugin.vue"

    viewer_items = List([]).tag(sync=True)
    viewer_selected = Unicode().tag(sync=True)

    waveband_items = List().tag(sync=True)
    waveband_selected = Any().tag(sync=True)  # Any to accept Nonetype
    resource_filter_coverage = Bool(False).tag(sync=True)
    resource_choices = List([]).tag(sync=True)
    resource_selected = Any().tag(sync=True)  # Any to accept Nonetype
    resources_loading = Bool(False).tag(sync=True)

    source = Unicode("").tag(sync=True)
    coord_follow_viewer_pan = Bool(False).tag(sync=True)
    viewer_centered = Bool(False).tag(sync=True)
    coordframe_choices = List([]).tag(sync=True)
    coordframe_selected = Unicode("icrs").tag(sync=True)
    radius = Float(1).tag(sync=True)
    radius_unit_items = List().tag(sync=True)
    radius_unit_selected = Unicode("deg").tag(sync=True)

    results_loading = Bool(False).tag(sync=True)
    data_loading = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # description displayed under plugin title in tray
        self._plugin_description = (
            "Download data products from VO-registered telescopes and missions."
        )

        self.viewer = ViewerSelect(
            self, "viewer_items", "viewer_selected", manual_options=["Manual"]
        )

        self.coordframe = SelectPluginComponent(
            self, items="coordframe_choices", selected="coordframe_selected"
        )
        self.coordframe.choices = [frame.lower() for frame in all_astropy_frames]
        self.coordframe.selected = self.coordframe.choices[0]

        self.radius_unit = UnitSelectPluginComponent(
            self, items="radius_unit_items", selected="radius_unit_selected"
        )
        self.radius_unit.choices = ["deg", "rad", "arcmin", "arcsec"]
        self.radius_unit.selected = "deg"

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
            self, items="resource_choices", selected="resource_selected"
        )
        self.resource.choices = []

        self.table.headers_avail = ["Title", "Instrument", "DateObs", "URL"]
        self.table.headers_visible = ["Title", "Instrument", "DateObs"]
        self._populate_url_only = False

        self.table.show_rowselect = True
        self.table.item_key = "URL"

        self.hub.subscribe(self, AddDataMessage, handler=self.vue_center_on_data)
        self.hub.subscribe(self, RemoveDataMessage, handler=self.vue_center_on_data)
        self.hub.subscribe(self, LinkUpdatedMessage, handler=self.vue_center_on_data)

    @observe("viewer_selected", type="change")
    def vue_viewer_changed(self, _=None):
        # Check mixin object initialized
        if not hasattr(self, "viewer"):
            return

        # Clear all existing subscriptions and resubscribe to selected viewer
        # NOTE: Viewer subscription needed regardless of coord_follow_viewer_pan in order
        #   to detect when coords are centered on viewer, regardless of viewer tracking
        for viewer in self.viewer.viewers:
            if viewer == self.viewer.selected_obj:
                viewer.state.add_callback(
                    "zoom_center_x",
                    lambda callback: self.vue_center_on_data(user_zoom_trigger=True),
                )
                viewer.state.add_callback(
                    "zoom_center_y",
                    lambda callback: self.vue_center_on_data(user_zoom_trigger=True),
                )
            else:
                # If not subscribed anyways, remove_callback should produce a no-op
                viewer.state.remove_callback(
                    "zoom_center_x",
                    lambda callback: self.vue_center_on_data(user_zoom_trigger=True),
                )
                viewer.state.remove_callback(
                    "zoom_center_y",
                    lambda callback: self.vue_center_on_data(user_zoom_trigger=True),
                )
        self.vue_center_on_data()

    @observe("coord_follow_viewer_pan", type="change")
    def _toggle_viewer_pan_tracking(self, _=None):
        """Detects when live viewer tracking toggle is clicked and centers on data if necessary"""
        # Center on data if we're enabling the toggle
        if self.coord_follow_viewer_pan:
            self.vue_center_on_data()

    def vue_center_on_data(self, _=None, user_zoom_trigger=False):
        """
        This vue method serves two purposes:
        * UI entrypoint for the manual viewer center button
        * Callback method for user panning (sub'ed to zoom_center_x/zoom_center_y)
        """
        # If plugin is in "Manual" mode, we should never
        # autocenter and potentially wipe the user's data
        if not self.viewer_selected or self.viewer_selected == "Manual":
            return

        # If the user panned but tracking not enabled, don't recenter
        if (user_zoom_trigger) and not self.coord_follow_viewer_pan:
            # Thus, we're no longer centered
            self.viewer_centered = False
            return

        self.center_on_data()

    def center_on_data(self):
        """
        If data is present in the default viewer, center the plugin's coordinates on
        the viewer's center WCS coordinates.
        """
        if not hasattr(self, "viewer"):
            # mixin object not yet initialized
            return

        # gets the current viewer
        viewer = self.viewer.selected_obj

        # nothing happens in the case there is no image in the viewer
        # additionally if the data does not have WCS
        if (
            len(self.app._jdaviz_helper.data_labels) < 1
            or viewer.state.reference_data is None
            or viewer.state.reference_data.coords is None
        ):
            self.source = ""
            return

        # Obtain center point of the current image and convert into sky coordinates
        if self.app._jdaviz_helper.plugins["Orientation"].align_by == "WCS":
            skycoord_center = SkyCoord(
                viewer.state.zoom_center_x, viewer.state.zoom_center_y, unit="deg"
            )
        else:
            skycoord_center = viewer.state.reference_data.coords.pixel_to_world(
                viewer.state.zoom_center_x, viewer.state.zoom_center_y
            )

        # Extract SkyCoord values as strings for plugin display
        ra_deg = skycoord_center.ra.deg
        dec_deg = skycoord_center.dec.deg
        frame = skycoord_center.frame.name.lower()

        # Show center value in plugin
        self.source = f"{ra_deg} {dec_deg}"
        self.coordframe_selected = frame

        self.viewer_centered = True

    @observe("waveband_selected", type="change")
    def vue_query_registry_resources(self, _=None):
        """
        This vue method serves as UI entrypoint for two actions:
        * Automatically fires when a waveband is selected
        * The manual resource refresh btn
        """
        self.query_registry_resources()

    @with_spinner(spinner_traitlet="resources_loading")
    def query_registry_resources(self, _=None):
        """
        Query Virtual Observatory registry for all SIA services
        that serve data in that waveband around the source.
        Then update the dropdown accordingly.
        """
        # If waveband was changed to nothing, immediately quit
        # Don't throw an error due to trigger by plugin init
        if not self.waveband_selected:
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
                    except Exception:
                        self.hub.broadcast(
                            SnackbarMessage(
                                f"Unable to resolve source coordinates: {self.source}",
                                sender=self,
                                color="error",
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
                )
            )
            raise

    @with_spinner(spinner_traitlet="results_loading")
    def vue_query_resource(self, _=None):
        """
        Once a specific VO resource is selected, query it with the user-specified source target.
        User input for source is first attempted to be parsed as a SkyCoord coordinate. If not,
        then attempts to parse as a target name.
        """
        # Reset Table
        self.table.items = []
        self._populate_url_only = False
        self.table.headers_visible = ["Title", "Instrument", "DateObs"]

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
                except Exception:
                    self.hub.broadcast(
                        SnackbarMessage(
                            f"Unable to resolve source coordinates: {self.source}",
                            sender=self,
                            color="error",
                        )
                    )
                    raise LookupError(
                        f"Unable to resolve source coordinates: {self.source}"
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
                    raise e
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
                )
            )
            raise

        try:
            self._populate_table(sia_results)
        except Exception as e:
            self.hub.broadcast(
                SnackbarMessage(
                    f"Unable to populate table for source {self.source}: {e}",
                    sender=self,
                    color="error",
                )
            )
            raise

    def _populate_table(
        self,
        sia_results,
        table_headers={"Title": "title", "Instrument": "instr", "DateObs": "dateobs"},
    ):
        for result in sia_results:
            table_entry = {"URL": result.getdataurl()}
            if not self._populate_url_only:
                try:
                    for header, attr in table_headers.items():
                        table_entry[header] = str(getattr(result, attr))
                except Exception as e:
                    self.hub.broadcast(
                        SnackbarMessage(
                            f"Can't get metadata columns. Switching table to URL-only: {e}",
                            sender=self,
                            color="warning",
                        )
                    )
                    # Hide all other incomplete columns and only load URL for subsequent rows
                    self.table.headers_visible = ["URL"]
                    self._populate_url_only = True
                    # Reset current entry to URL only
                    table_entry = {"URL": result.getdataurl()}
            # Table widget only supports JSON-verification for serial table additions.
            # For improved performance with larger tables, a `table.add_items` that accepts
            # a table of elements should be implemented
            self.table.add_item(table_entry)
        self.hub.broadcast(
            SnackbarMessage(
                f"{len(sia_results)} SIA results populated!",
                sender=self,
                color="success",
            )
        )

    def vue_load_selected_data(self, event=None):
        """UI entrypoint for load data btn"""
        self.load_selected_data()

    @with_spinner(spinner_traitlet="data_loading")
    def load_selected_data(self, _=None):
        """Load the files selected by the user in the table"""
        if (
            self.app._jdaviz_helper.plugins["Orientation"].align_by != "WCS"
            and len(self.app.data_collection) > 0
        ):
            error_msg = (
                "WCS linking is not enabled; data layers may not be aligned. To align, "
                "switch link type to WCS in the Orientation plugin"
            )
            self.hub.broadcast(SnackbarMessage(error_msg, sender=self, color="warning"))

        for entry in self.table.selected_rows:
            try:
                self.app._jdaviz_helper.load_data(
                    str(entry["URL"]),  # Open URL as FITS object
                    data_label=f"{self.source}_{self.resource_selected}_{entry.get('Title', entry.get('URL', ''))}",  # noqa: E501
                    cache=False,
                    timeout=1e6,  # Set to arbitrarily large value to prevent timeouts
                )
            except Exception as e:
                self.hub.broadcast(
                    SnackbarMessage(
                        f"Unable to load file to viewer: {entry['URL']}: {e}",
                        sender=self,
                        color="error",
                    )
                )
        # Clear selected entries' checkboxes on table
        self.table.selected_rows = []
