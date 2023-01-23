import math
import numpy as np
from traitlets import Bool, Unicode

from astropy import units as u
from glue.core import BaseData
from glue.core.subset import RoiSubsetState
from glue.core.subset_group import GroupedSubset

from jdaviz.configs.cubeviz.plugins.viewers import CubevizImageView
from jdaviz.configs.imviz.helper import data_has_valid_wcs
from jdaviz.configs.imviz.plugins.viewers import ImvizImageView
from jdaviz.configs.mosviz.plugins.viewers import MosvizImageView, MosvizProfile2DView
from jdaviz.configs.specviz.plugins.viewers import SpecvizProfileView
from jdaviz.core.events import ViewerAddedMessage
from jdaviz.core.registries import tool_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.core.marks import PluginScatter

__all__ = ['CoordsInfo']


@tool_registry('g-coords-info')
class CoordsInfo(TemplateMixin):
    template_file = __file__, "coords_info.vue"
    icon = Unicode("").tag(sync=True)

    row1a_title = Unicode("").tag(sync=True)
    row1a_text = Unicode("").tag(sync=True)
    row1b_title = Unicode("").tag(sync=True)
    row1b_text = Unicode("").tag(sync=True)
    row1_unreliable = Bool(False).tag(sync=True)

    row2_title = Unicode("").tag(sync=True)
    row2_text = Unicode("").tag(sync=True)
    row2_unreliable = Bool(False).tag(sync=True)

    row3_title = Unicode("").tag(sync=True)
    row3_text = Unicode("").tag(sync=True)
    row3_unreliable = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._marks = {}
        self._x, self._y = None, None  # latest known cursor positions

        # subscribe/unsubscribe to mouse events across all existing viewers
        for viewer in self.app._viewer_store.values():
            self._create_viewer_callbacks(viewer)

        # subscribe to mouse events on any new viewers
        self.hub.subscribe(self, ViewerAddedMessage, handler=self._on_viewer_added)

    def _create_viewer_callbacks(self, viewer):
        if isinstance(viewer,
                      (SpecvizProfileView,
                       ImvizImageView,
                       CubevizImageView,
                       MosvizImageView,
                       MosvizProfile2DView)):
            callback = self._viewer_callback(viewer, self._viewer_mouse_event)
            viewer.add_event_callback(callback, events=['mousemove', 'mouseleave', 'mouseenter'])

            viewer.state.add_callback('layers', lambda msg: self._layers_changed(viewer))

    def _on_viewer_added(self, msg):
        self._create_viewer_callbacks(self.app.get_viewer_by_id(msg.viewer_id))

    @property
    def marks(self):
        """
        Access the marks created by this plugin.
        """
        if self._marks:
            # TODO: replace with cache property?
            return self._marks

        # create marks for each of the spectral viewers (will need a listener event to create marks
        # for new viewers if dynamic creation of spectral viewers is ever supported)
        for id, viewer in self.app._viewer_store.items():
            if isinstance(viewer, SpecvizProfileView):
                self._marks[id] = PluginScatter(viewer,
                                                marker='rectangle', stroke_width=1,
                                                visible=False)
                viewer.figure.marks = viewer.figure.marks + [self._marks[id]]
        return self._marks

    def as_text(self):
        return (f"{self.row1a_title} {self.row1a_text} {self.row1b_title} {self.row1b_text}".strip(),  # noqa
                f"{self.row2_title} {self.row2_text}".strip(),
                f"{self.row3_title} {self.row3_text}".strip())

    def reset_coords_display(self):
        self.row1a_title = '\u00A0'  # to force empty line if no other content
        self.row1a_text = ""
        self.row1b_title = ""
        self.row1b_text = ""
        self.row1_unreliable = False

        self.row2_title = '\u00A0'
        self.row2_text = ""
        self.row2_unreliable = False

        self.row3_title = '\u00A0'
        self.row3_text = ""
        self.row3_unreliable = False

        self.icon = ""

    def _viewer_mouse_clear_event(self, viewer, data=None):
        self.reset_coords_display()
        marks = self.marks.get(viewer._reference_id)
        if marks is not None:
            marks.visible = False

    def _viewer_mouse_event(self, viewer, data):
        if data['event'] in ['mouseleave', 'mouseenter']:
            return self._viewer_mouse_clear_event(viewer, data)

        if len(self.app.data_collection) < 1:
            return self._viewer_mouse_clear_event(viewer)

        # otherwise a mousemove event, we need to get cursor coordinates and update the display

        # Extract data coordinates - these are pixels in the reference image
        x = data['domain']['x']
        y = data['domain']['y']

        if x is None or y is None:  # Out of bounds
            return self._viewer_mouse_clear_event(viewer)

        # update last known cursor position (so another event like a change in layers can update
        # the coordinates with the last known position)
        self._x, self._y = x, y
        self.update_display(viewer, x=x, y=y)

    def _layers_changed(self, viewer):
        if self._x is None or self._y is None:
            return

        # update display for a (possible) change to the active layer based on the last known
        # cursor position
        self.update_display(viewer, self._x, self._y)

    def update_display(self, viewer, x, y):
        """
        """
        if isinstance(viewer, SpecvizProfileView):
            self._spectrum_viewer_update(viewer, x, y)
        elif isinstance(viewer,
                        (ImvizImageView, CubevizImageView, MosvizImageView, MosvizProfile2DView)):
            self._image_viewer_update(viewer, x, y)

    def _image_viewer_update(self, viewer, x, y):
        # Display the current cursor coordinates (both pixel and world) as
        # well as data values. For now we use the first dataset in the
        # viewer for the data values.

        # Extract first dataset from visible layers and use this for coordinates - the choice
        # of dataset shouldn't matter if the datasets are linked correctly
        active_layer = viewer.active_image_layer
        if active_layer is None:
            self._viewer_mouse_clear_event(viewer)
            return

        image = active_layer.layer
        self.icon = self.app.state.layer_icons.get(image.label, '')  # noqa

        unreliable_pixel, unreliable_world = False, False

        # separate logic for each viewer type, ultimately needs to result in extracting sky coords
        if isinstance(viewer, ImvizImageView):
            x, y, coords_status, (unreliable_world, unreliable_pixel) = viewer._get_real_xy(image, x, y)  # noqa
            if coords_status:
                try:
                    sky = image.coords.pixel_to_world(x, y).icrs
                except Exception:  # WCS might not be celestial
                    coords_status = False
                    self.reset_coords_display()

        elif isinstance(viewer, CubevizImageView):
            # TODO: This assumes data_collection[0] is the main reference
            #  data for this application. This section will need to be updated
            #  when that is no longer true.
            # Hack to insert WCS for generated 2D and 3D images using FLUX cube WCS.
            if 'Plugin' in image.meta:
                coo_data = self.app.data_collection[0]
            else:
                coo_data = image

            # Hack around various WCS propagation issues in Cubeviz.
            if '_orig_wcs' in coo_data.meta:
                sky = coo_data.meta['_orig_wcs'].pixel_to_world(x, y, viewer.state.slices[-1])[0].icrs  # noqa
                coords_status = True
            elif data_has_valid_wcs(coo_data):
                try:
                    sky = coo_data.coords.pixel_to_world(x, y, viewer.state.slices[-1])[-1].icrs
                except Exception:
                    coords_status = False
                else:
                    coords_status = True
            else:  # pragma: no cover
                self.reset_coords_display()

        elif isinstance(viewer, MosvizImageView):

            if data_has_valid_wcs(image, ndim=2):
                try:
                    sky = image.coords.pixel_to_world(x, y).icrs
                except Exception:  # WCS might not be celestial  # pragma: no cover
                    coords_status = False
                else:
                    coords_status = True
            else:  # pragma: no cover
                self.reset_coords_display()

        elif isinstance(viewer, MosvizProfile2DView):
            coords_status = False

        if coords_status:
            celestial_coordinates = sky.to_string('hmsdms', precision=4, pad=True).split()
            celestial_coordinates_deg = sky.to_string('decimal', precision=10, pad=True).split()
            world_ra = celestial_coordinates[0]
            world_dec = celestial_coordinates[1]
            world_ra_deg = celestial_coordinates_deg[0]
            world_dec_deg = celestial_coordinates_deg[1]

            if "nan" in (world_ra, world_dec, world_ra_deg, world_dec_deg):
                self.reset_coords_display()

            self.row2_title = 'World'
            self.row2_text = f'{world_ra} {world_dec} (ICRS)'
            self.row2_unreliable = unreliable_world
            self.row3_title = ''
            self.row3_text = f'{world_ra_deg} {world_dec_deg} (deg)'
            self.row3_unreliable = unreliable_world

        maxsize = int(np.ceil(np.log10(np.max(image.shape)))) + 3
        fmt = 'x={0:0' + str(maxsize) + '.1f} y={1:0' + str(maxsize) + '.1f}'
        self.row1a_title = 'Pixel'
        self.row1a_text = (fmt.format(x, y))
        self.row1_unreliable = unreliable_pixel

        # Extract data values at this position.
        # TODO: for now we just use the first visible layer but we should think
        # of how to display values when multiple datasets are present.

        # Extract data values at this position.
        # Check if shape is [x, y, z] or [y, x] and show value accordingly.
        if image.ndim == 3:
            # needed for cubeviz
            ix_shape = 0
            iy_shape = 1
        elif image.ndim == 2:
            ix_shape = 1
            iy_shape = 0
        else:  # pragma: no cover
            raise ValueError(f'does not support ndim={image.ndim}')

        if (-0.5 < x < image.shape[ix_shape] - 0.5 and -0.5 < y < image.shape[iy_shape] - 0.5
                and hasattr(active_layer, 'attribute')):
            attribute = active_layer.attribute
            if isinstance(viewer, (ImvizImageView, MosvizImageView, MosvizProfile2DView)):
                value = image.get_data(attribute)[int(round(y)), int(round(x))]
                unit = image.get_component(attribute).units
            elif isinstance(viewer, CubevizImageView):
                arr = image.get_component(attribute).data
                unit = image.get_component(attribute).units
                if image.ndim == 3:
                    value = arr[int(round(x)), int(round(y)), viewer.state.slices[-1]]
                else:  # 2
                    value = arr[int(round(y)), int(round(x))]
            self.row1b_title = 'Value'
            self.row1b_text = f'{value:+10.5e} {unit}'
        else:
            self.row1b_title = ''
            self.row1b_text = ''

    def _spectrum_viewer_update(self, viewer, x, y):
        self.row1a_title = 'Cursor'
        self.row1a_text = f'{x:10.5e}, {y:10.5e}'

        # show the locked marker/coords only if either no tool or the default tool is active
        locking_active = viewer.toolbar.active_tool_id in viewer.toolbar.default_tool_priority + [None]  # noqa
        if not locking_active:
            self.row2_title = '\u00A0'
            self.row2_text = ''
            self.row3_title = '\u00A0'
            self.row3_text = ''
            self.icon = ''
            self.marks[viewer._reference_id].visible = False
            return

        # Snap to the closest data point, not the actual mouse location.
        sp = None
        closest_i = None
        closest_wave = None
        closest_flux = None
        closest_icon = ''
        closest_distance = None
        for lyr in viewer.state.layers:
            if not lyr.visible:
                continue
            if isinstance(lyr.layer, GroupedSubset):
                if not isinstance(lyr.layer.subset_state, RoiSubsetState):
                    # then this is a SPECTRAL subset
                    continue
            elif ((not isinstance(lyr.layer, BaseData)) or (lyr.layer.ndim not in (1, 3))
                    or (not lyr.visible)):
                continue

            try:
                # Cache should have been populated when spectrum was first plotted.
                # But if not (maybe user changed statistic), we cache it here too.
                statistic = getattr(viewer.state, 'function', None)
                cache_key = (lyr.layer.label, statistic)
                if cache_key in self.app._get_object_cache:
                    sp = self.app._get_object_cache[cache_key]
                else:
                    sp = self.app.get_data_from_viewer('spectrum-viewer', lyr.layer.label)
                    self.app._get_object_cache[cache_key] = sp

                # Out of range in spectral axis.
                if x < sp.spectral_axis.value.min() or x > sp.spectral_axis.value.max():
                    continue

                cur_i = np.argmin(abs(sp.spectral_axis.value - x))
                cur_wave = sp.spectral_axis[cur_i]
                cur_flux = sp.flux[cur_i]

                dx = cur_wave.value - x
                dy = cur_flux.value - y
                cur_distance = math.sqrt(dx * dx + dy * dy)
                if (closest_distance is None) or (cur_distance < closest_distance):
                    closest_distance = cur_distance
                    closest_i = cur_i
                    closest_wave = cur_wave
                    closest_flux = cur_flux
                    closest_icon = self.app.state.layer_icons.get(lyr.layer.label)
            except Exception:  # nosec
                # Something is loaded but not the right thing
                continue

        if closest_wave is None:
            self._viewer_mouse_clear_event(viewer)
            return

        self.row2_title = 'Wave'
        self.row2_text = f'{closest_wave.value:10.5e} {closest_wave.unit.to_string()}'
        if closest_wave.unit != u.pix:
            self.row2_text += f' ({int(closest_i)} pix)'

        self.row3_title = 'Flux'
        self.row3_text = f'{closest_flux.value:10.5e} {closest_flux.unit.to_string()}'

        self.icon = closest_icon

        self.marks[viewer._reference_id].update_xy([closest_wave.value], [closest_flux.value])  # noqa
        self.marks[viewer._reference_id].visible = True
