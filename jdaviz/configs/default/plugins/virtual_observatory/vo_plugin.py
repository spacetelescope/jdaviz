from astropy.coordinates.builtin_frames import __all__ as all_astropy_frames
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy import units as u

from pyvo.utils import vocabularies
from pyvo import registry
from pyvo.dal.exceptions import DALFormatError
from requests.exceptions import ConnectionError as RequestConnectionError
from traitlets import Bool, Unicode, Any, List, Int, observe

from jdaviz.core.events import SnackbarMessage, AddDataMessage, RemoveDataMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (
    PluginTemplateMixin,
    AddResultsMixin,
    TableMixin,
    ViewerSelect,
)

__all__ = ["VoPlugin"]


@tray_registry("VoPlugin", label="Virtual Observatory")
class VoPlugin(PluginTemplateMixin, AddResultsMixin, TableMixin):
    """Plugin to query the Virtual Observatory and load data into Imviz"""

    template_file = __file__, "vo_plugin.vue"

    viewer_items = List([]).tag(sync=True)
    viewer_selected = Unicode().tag(sync=True)

    wavebands = List().tag(sync=True)
    waveband_selected = Any().tag(sync=True)  # Any to accept Nonetype
    resource_filter_coverage = Bool(True).tag(sync=True)
    resources = List([]).tag(sync=True)
    resource_selected = Any().tag(sync=True)  # Any to accept Nonetype
    resources_loading = Bool(False).tag(sync=True)

    source = Unicode("").tag(sync=True)
    coordframes = List([]).tag(sync=True)
    coordframe_selected = Unicode("icrs").tag(sync=True)
    radius_deg = Int(1).tag(sync=True)

    results_loading = Bool(False).tag(sync=True)
    data_loading = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.viewer = ViewerSelect(
            self, "viewer_items", "viewer_selected", manual_options=["Manual"]
        )

        # Waveband properties to filter available registry resources
        self.wavebands = [
            w.lower() for w in vocabularies.get_vocabulary("messenger")["terms"]
        ]
        self.waveband_selected = None

        self._full_registry_results = None
        self.resource_selected = None

        self.coordframes = [frame.lower() for frame in all_astropy_frames]

        self.table.headers_avail = ["Title", "Instrument", "DateObs", "URL"]
        self.table.headers_visible = ["Title", "Instrument", "DateObs"]
        self._populate_url_only = False

        self.table.show_rowselect = True
        self.table.item_key = "URL"

        self.hub.subscribe(self, AddDataMessage, handler=self._center_on_data)
        self.hub.subscribe(self, RemoveDataMessage, handler=self._center_on_data)

    @observe("viewer_selected", "change")
    def _center_on_data(self, _=None):
        """
        If data is present in the default viewer, center the plugin's coordinates on
        the viewer's center WCS coordinates.
        """
        if not hasattr(self, "viewer"):
            # mixin object not yet initialized
            return
        if self.viewer_selected == "Manual":
            return

        # gets the current viewer
        if self.viewer_selected:
            viewer = self.viewer.selected_obj

        # nothing happens in the case there is no image in the viewer
        # additionally if the data does not have WCS
        if (
            viewer.state.reference_data is None
            or viewer.state.reference_data.coords is None
        ):
            return

        # Obtain center point of the current image and convert into sky coordinates
        x_center = (viewer.state.x_min + viewer.state.x_max) * 0.5
        y_center = (viewer.state.y_min + viewer.state.y_max) * 0.5
        skycoord_center = viewer.state.reference_data.coords.pixel_to_world(
            x_center, y_center
        )

        # Extract SkyCoord values as strings for plugin display
        ra_deg = skycoord_center.ra.deg
        dec_deg = skycoord_center.dec.deg
        frame = skycoord_center.frame.name.lower()

        # Show center value in plugin
        self.source = f"{ra_deg} {dec_deg}"
        self.coordframe_selected = frame

    @observe("waveband_selected", "change")
    def vue_query_registry_resources(self, _=None):
        """
        Query Virtual Observatory registry for all SIA services
        that serve data in that waveband around the source.
        Then update the dropdown accordingly.
        """
        # If missing either required fields, immediately quit
        if not self.source or not self.waveband_selected:
            return

        # Clear existing resources list
        self.resources = []
        self.resource_selected = None
        self.resources_loading = True  # Start loading bar
        try:
            # First parse user-provided source as direct coordinates
            coord = SkyCoord(self.source, unit=u.deg, frame=self.coordframe_selected)
        except:
            try:
                # If that didn't work, try parsing it as an object name
                coord = SkyCoord.from_name(self.source, frame=self.coordframe_selected)
            except Exception:
                self.resources_loading = False  # Stop loading bar
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

        try:
            registry_args = [
                registry.Servicetype("sia"),
                registry.Waveband(self.waveband_selected),
            ]
            if coord != None and self.resource_filter_coverage:
                registry_args.append(
                    registry.Spatial(coord, self.radius_deg, intersect="overlaps")
                )
            self._full_registry_results = registry.search(*registry_args)
            self.resources = list(self._full_registry_results.getcolumn("short_name"))
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
        finally:
            self.resources_loading = False  # Stop loading bar

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

        self.results_loading = True  # Start loading spinner
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
            except:
                try:
                    # If that didn't work, try parsing it as an object name
                    coord = SkyCoord.from_name(
                        self.source, frame=self.coordframe_selected
                    )
                except Exception:
                    raise LookupError(
                        f"Unable to resolve source coordinates: {self.source}"
                    )

            # Once coordinate lookup is complete, search service using these coords.
            sia_results = sia_service.search(
                coord,
                size=((self.radius_deg * u.deg) if self.radius_deg > 0 else None),
                format="image/fits",
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
                )
            )
            raise
        finally:
            self.results_loading = False  # Stop loading spinner

        try:
            for result in sia_results:
                table_entry = {"URL": result.getdataurl()}
                if not self._populate_url_only:
                    try:
                        table_entry["Title"] = str(result.title)
                        table_entry["Instrument"] = str(result.instr)
                        table_entry["DateObs"] = str(result.dateobs)
                    except Exception as e:
                        self.hub.broadcast(
                            SnackbarMessage(
                                f"Can't get metadata columns. Switching table to URL-only: {e}",
                                sender=self,
                                color="warning",
                            )
                        )
                        self.table.headers_visible = ["URL"]
                        self._populate_url_only = True
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
        except Exception as e:
            self.hub.broadcast(
                SnackbarMessage(
                    f"Unable to populate table for source {self.source}: {e}",
                    sender=self,
                    color="error",
                )
            )
            raise

    def vue_load_selected_data(self, _=None):
        """Load the files selected by the user in the table"""
        self.data_loading = True  # Start loading spinner
        for entry in self.table.selected_rows:
            try:
                self.app._jdaviz_helper.load_data(
                    fits.open(str(entry["URL"])),  # Open URL as FITS object
                    data_label=f"{self.source}_{self.resource_selected}_{entry.get('Title', entry.get('URL', ''))}",  # noqa: E501
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
        self.data_loading = False  # Stop loading spinner
