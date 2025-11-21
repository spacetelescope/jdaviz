from astropy.coordinates.builtin_frames import __all__ as all_astropy_frames
from astropy.coordinates import SkyCoord
from astropy import units as u


from traitlets import Bool, Unicode, List, Float, observe

from jdaviz.core.custom_traitlets import IntHandleEmpty
from jdaviz.core.events import (
    SnackbarMessage,
    AddDataMessage,
    RemoveDataMessage,
    LinkUpdatedMessage,
)
from jdaviz.core.registries import loader_resolver_registry
from jdaviz.core.template_mixin import (
    ViewerSelect,
    SelectPluginComponent,
    UnitSelectPluginComponent,
    with_spinner,
)
from jdaviz.core.loaders.resolvers import BaseResolver
from jdaviz.core.user_api import LoaderUserApi

__all__ = ["AstroqueryResolver"]


@loader_resolver_registry("astroquery")
class AstroqueryResolver(BaseResolver):
    template_file = __file__, "astroquery.vue"

    viewer_items = List([]).tag(sync=True)
    viewer_selected = Unicode().tag(sync=True)

    source = Unicode("").tag(sync=True)
    coord_follow_viewer_pan = Bool(False).tag(sync=True)
    viewer_centered = Bool(False).tag(sync=True)
    coordframe_choices = List([]).tag(sync=True)
    coordframe_selected = Unicode("icrs").tag(sync=True)
    radius = Float(1).tag(sync=True)
    radius_unit_items = List().tag(sync=True)
    radius_unit_selected = Unicode("deg").tag(sync=True)

    telescope_items = List([]).tag(sync=True)
    telescope_selected = Unicode().tag(sync=True)

    max_results = IntHandleEmpty(1000).tag(sync=True)
    reached_max_results = Bool(False).tag(sync=True)

    results_loading = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._output = None

        self.viewer = ViewerSelect(
            self, "viewer_items", "viewer_selected", manual_options=["Manual"],
            filters=['is_image_viewer']
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

        self.telescope = SelectPluginComponent(
            self, items="telescope_items", selected="telescope_selected",
            manual_options=['SDSS', 'Gaia']
        )

        self.hub.subscribe(self, AddDataMessage, handler=self.vue_center_on_data)
        self.hub.subscribe(self, RemoveDataMessage, handler=self.vue_center_on_data)
        self.hub.subscribe(self, LinkUpdatedMessage, handler=self.vue_center_on_data)

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
                self.reached_max_results = False
                output = None
        elif self.telescope.selected == 'Gaia':
            from astroquery.gaia import Gaia

            Gaia.ROW_LIMIT = self.max_results
            output = Gaia.query_object(skycoord_center, radius=radius)
        else:
            raise NotImplementedError(f"Querying for {self.telescope.selected} is not supported.")

        if output is not None and len(output) > self.max_results:
            output = output[:self.max_results]
            self.reached_max_results = True
        else:
            self.reached_max_results = False
        self._output = output

        self._resolver_input_updated()

    def vue_query_archive(self, _=None):
        self.query_archive()

    @property
    def is_valid(self):
        # this resolver does not accept any direct, (default_input = None), so can
        # always be considered valid
        return True

    def parse_input(self):
        return self._output
