import math
import numpy as np
from traitlets import Bool, Unicode, observe

from astropy import units as u
from glue.core import BaseData
from glue.core.subset_group import GroupedSubset
from glue_jupyter.bqplot.image.layer_artist import BqplotImageSubsetLayerArtist

from jdaviz.configs.cubeviz.plugins.viewers import CubevizImageView
from jdaviz.configs.imviz.plugins.viewers import ImvizImageView
from jdaviz.configs.mosviz.plugins.viewers import MosvizImageView, MosvizProfile2DView
from jdaviz.configs.specviz.plugins.viewers import SpecvizProfileView
from jdaviz.core.events import ViewerAddedMessage
from jdaviz.core.helpers import data_has_valid_wcs
from jdaviz.core.marks import PluginScatter
from jdaviz.core.registries import tool_registry
from jdaviz.core.template_mixin import TemplateMixin, DatasetSelectMixin
from jdaviz.utils import get_subset_type

__all__ = ['CoordsInfo']


@tool_registry('g-coords-info')
class CoordsInfo(TemplateMixin, DatasetSelectMixin):
    template_file = __file__, "coords_info.vue"

    _supported_viewer_classes = (SpecvizProfileView,
                                 ImvizImageView,
                                 CubevizImageView,
                                 MosvizImageView,
                                 MosvizProfile2DView)

    _viewer_classes_with_marker = (SpecvizProfileView,)

    dataset_icon = Unicode("").tag(sync=True)  # option for layer (auto, none, or specific layer)
    icon = Unicode("").tag(sync=True)  # currently exposed layer

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
        self._dict = {}  # dictionary representation of current mouseover info
        self._x, self._y = None, None  # latest known cursor positions

        # subscribe/unsubscribe to mouse events across all existing viewers
        viewer_refs = []
        for viewer in self.app._viewer_store.values():
            if isinstance(viewer, self._supported_viewer_classes):
                self._create_viewer_callbacks(viewer)
                viewer_refs.append(viewer.reference_id)

        self.dataset._manual_options = ['auto', 'none']
        self.dataset.filters = ['layer_in_viewers']
        if self.app.config == 'imviz':
            # filter out scatter-plot entries (from add_markers API, for example)
            self.dataset.add_filter('is_image')
        # we also want to include auto-collapsed spectra (spatial subsets)
        self.dataset._cubeviz_include_spatial_subsets()

        # subscribe to mouse events on any new viewers
        self.hub.subscribe(self, ViewerAddedMessage, handler=self._on_viewer_added)

    def _create_marks_for_viewer(self, viewer, id=None):
        if id is None:
            id = viewer.reference_id
        if id in self._marks:
            return
        self._marks[id] = PluginScatter(viewer,
                                        marker='rectangle', stroke_width=1,
                                        visible=False)
        viewer.figure.marks = viewer.figure.marks + [self._marks[id]]

    def _create_viewer_callbacks(self, viewer):
        if isinstance(viewer, self._supported_viewer_classes):
            if isinstance(viewer, self._viewer_classes_with_marker):
                self._create_marks_for_viewer(viewer)
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
            if isinstance(viewer, self._viewer_classes_with_marker):
                self._create_marks_for_viewer(viewer, id)
        return self._marks

    def as_text(self):
        return (f"{self.row1a_title} {self.row1a_text} {self.row1b_title} {self.row1b_text}".strip(),  # noqa
                f"{self.row2_title} {self.row2_text}".strip(),
                f"{self.row3_title} {self.row3_text}".strip())

    def as_dict(self):
        return self._dict

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
        self._dict = {}

    def _viewer_mouse_clear_event(self, viewer, data=None):
        self.reset_coords_display()
        marks = self.marks.get(viewer._reference_id)
        if marks is not None:
            marks.visible = False

    def _viewer_mouse_event(self, viewer, data):
        if data['event'] in ('mouseleave', 'mouseenter'):
            self._viewer_mouse_clear_event(viewer, data)
            return

        if len(self.app.data_collection) < 1:
            self._viewer_mouse_clear_event(viewer)
            return

        # otherwise a mousemove event, we need to get cursor coordinates and update the display

        # Extract data coordinates - these are pixels in the reference image
        x = data['domain']['x']
        y = data['domain']['y']

        if x is None or y is None:  # Out of bounds
            self._viewer_mouse_clear_event(viewer)
            return

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

    @observe('dataset_selected')
    def _selected_dataset_changed(self, *args):
        if self.dataset_selected == 'auto':
            self.dataset_icon = 'mdi-auto-fix'
        elif self.dataset_selected == 'none':
            self.dataset_icon = 'mdi-cursor-default'
        else:
            self.dataset_icon = self.app.state.layer_icons.get(self.dataset_selected, '')

    def vue_next_layer(self, *args, **kwargs):
        self.dataset.select_next()

    def update_display(self, viewer, x, y):
        self._dict = {}
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

        if self.dataset.selected == 'auto':
            image = active_layer.layer
        elif self.dataset.selected == 'none':
            active_layer = viewer.layers[0].state
            image = viewer.layers[0].layer
        else:
            for layer in viewer.layers:
                if layer.layer.label == self.dataset.selected and layer.visible:
                    if isinstance(layer, BqplotImageSubsetLayerArtist):
                        # cannot expose info for spatial subset layers
                        continue
                    active_layer = layer.state
                    image = layer.layer
                    break
            else:
                image = None

        unreliable_pixel, unreliable_world = False, False

        self._dict['axes_x'] = x
        self._dict['axes_x:unit'] = 'pix'
        self._dict['axes_y'] = y
        self._dict['axes_y:unit'] = 'pix'

        # set default empty values
        if self.dataset.selected != 'none' and image is not None:
            self.icon = self.app.state.layer_icons.get(image.label, '')  # noqa
            self._dict['data_label'] = image.label

        # Separate logic for each viewer type, ultimately needs to result in extracting sky coords.
        # NOTE: pixel_to_world axes order is opposite of array value axes order, so...
        #   3D: pixel_to_world(z, y, x) -> arr[x, y, z]
        #   2D: pixel_to_world(x, y) -> arr[y, x]
        if self.dataset.selected == 'none' or image is None:
            self.icon = 'mdi-cursor-default'
            self._dict['data_label'] = ''
            coords_status = False

        elif isinstance(viewer, ImvizImageView):
            x, y, coords_status, (unreliable_world, unreliable_pixel) = viewer._get_real_xy(image, x, y)  # noqa
            if coords_status:
                try:
                    sky = image.coords.pixel_to_world(x, y).icrs
                except Exception:  # WCS might not be celestial
                    coords_status = False

        elif isinstance(viewer, CubevizImageView):
            # TODO: This assumes data_collection[0] is the main reference
            #  data for this application. This section will need to be updated
            #  when that is no longer true.
            # Hack to insert WCS for generated 2D and 3D images using FLUX cube WCS.
            if 'Plugin' in getattr(image, 'meta', {}) and not image.coords:
                coo_data = self.app.data_collection[0]
            else:
                coo_data = image

            if '_orig_spec' in getattr(coo_data, 'meta', {}):
                # Hack around various WCS propagation issues in Cubeviz, example:
                # https://github.com/glue-viz/glue-astronomy/issues/75
                data_wcs = coo_data.meta['_orig_spec'].wcs
                wcs_ndim = 3
            elif data_has_valid_wcs(coo_data):
                data_wcs = coo_data.coords
                wcs_ndim = coo_data.ndim
            else:
                data_wcs = None

            if data_wcs:
                try:
                    if wcs_ndim == 3:
                        sky = data_wcs.pixel_to_world(viewer.state.slices[-1], y, x)[1].icrs
                    else:  # wcs_ndim == 2
                        sky = data_wcs.pixel_to_world(x, y).icrs
                except Exception:
                    coords_status = False
                else:
                    coords_status = True
            else:
                self.reset_coords_display()
                coords_status = False

            slice_plugin = self.app._jdaviz_helper.plugins.get('Slice', None)
            if slice_plugin is not None and len(image.shape) == 3:
                # float to be compatible with default value of nan
                self._dict['slice'] = float(slice_plugin.slice)
                self._dict['spectral_axis'] = slice_plugin.wavelength
                self._dict['spectral_axis:unit'] = slice_plugin._obj.wavelength_unit

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
                coords_status = False

        elif isinstance(viewer, MosvizProfile2DView):
            self._dict['spectral_axis'] = self._dict['axes_x']
            self._dict['spectral_axis:unit'] = self._dict['axes_x:unit']
            self._dict['value'] = self._dict['axes_y']
            self._dict['value:unit'] = self._dict['axes_y:unit']
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
            # TODO: use sky directly, but need to figure out how to have a compatible "blank" entry
            self._dict['world'] = (sky.ra.value, sky.dec.value)
            self._dict['world:unreliable'] = unreliable_world
        else:
            self.row2_title = '\u00A0'
            self.row2_text = ""
            self.row2_unreliable = False

            self.row3_title = '\u00A0'
            self.row3_text = ""
            self.row3_unreliable = False

        maxsize = int(np.ceil(np.log10(np.max(active_layer.layer.shape)))) + 3
        fmt = 'x={0:0' + str(maxsize) + '.1f} y={1:0' + str(maxsize) + '.1f}'
        self.row1a_title = 'Pixel'
        self.row1a_text = (fmt.format(x, y))
        self.row1_unreliable = unreliable_pixel
        self._dict['pixel'] = (float(x), float(y))
        self._dict['pixel:unreliable'] = unreliable_pixel

        # Extract data values at this position.
        # TODO: for now we just use the first visible layer but we should think
        # of how to display values when multiple datasets are present.

        if self.dataset.selected == 'none' or image is None:
            # no data values to extract
            self.row1b_title = ''
            self.row1b_text = ''
            return

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
            self._dict['value'] = float(value)
            self._dict['value:unit'] = unit
            self._dict['value:unreliable'] = unreliable_pixel
        else:
            self.row1b_title = ''
            self.row1b_text = ''

    def _spectrum_viewer_update(self, viewer, x, y):
        def _cursor_fallback():
            self._dict['axes_x'] = x
            self._dict['axes_x:unit'] = viewer.state.x_display_unit
            self._dict['axes_y'] = y
            self._dict['axes_y:unit'] = viewer.state.y_display_unit
            self._dict['data_label'] = ''

        def _copy_axes_to_spectral():
            self._dict['spectral_axis'] = self._dict['axes_x']
            self._dict['spectral_axis:unit'] = self._dict['axes_x:unit']
            self._dict['value'] = self._dict['axes_y']
            self._dict['value:unit'] = self._dict['axes_y:unit']

        if not len(viewer.state.layers):
            return

        self.row1a_title = 'Cursor'
        self.row1a_text = f'{x:10.5e}, {y:10.5e}'

        # show the locked marker/coords only if either no tool or the default tool is active
        if self.dataset.selected == 'none':
            self.row2_title = '\u00A0'
            self.row2_text = ''
            self.row3_title = '\u00A0'
            self.row3_text = ''
            self.icon = 'mdi-cursor-default'
            self.marks[viewer._reference_id].visible = False
            _cursor_fallback()
            _copy_axes_to_spectral()
            return

        # Snap to the closest data point, not the actual mouse location.
        sp = None
        closest_i = None
        closest_wave = None
        closest_flux = None
        closest_icon = 'mdi-cursor-default'
        closest_distance = None
        for lyr in viewer.state.layers:
            if self.dataset.selected == 'auto' and not lyr.visible:
                continue
            if self.dataset.selected != 'auto' and self.dataset.selected != lyr.layer.label:
                continue

            if isinstance(lyr.layer, GroupedSubset):
                subset_state = getattr(lyr.layer, 'subset_state', None)
                if subset_state is None:
                    continue
                subset_type = get_subset_type(subset_state)
                if subset_type == 'spectral':
                    # then this is a SPECTRAL subset
                    continue
                # For use later in data retrieval
                subset_label = lyr.layer.label
                data_label = lyr.layer.data.label
            elif ((not isinstance(lyr.layer, BaseData)) or (lyr.layer.ndim not in (1, 3))):
                continue
            else:
                subset_label = None
                data_label = lyr.layer.label

            try:
                # Cache should have been populated when spectrum was first plotted.
                # But if not (maybe user changed statistic), we cache it here too.
                statistic = getattr(viewer.state, 'function', None)
                cache_key = (lyr.layer.label, statistic)
                if cache_key in self.app._get_object_cache:
                    sp = self.app._get_object_cache[cache_key]
                else:
                    sp = self._specviz_helper.get_data(data_label=data_label,
                                                       spatial_subset=subset_label)
                    self.app._get_object_cache[cache_key] = sp

                # Calculations have to happen in the frame of viewer display units.
                disp_wave = sp.spectral_axis.to_value(viewer.state.x_display_unit, u.spectral())
                disp_flux = sp.flux.to_value(viewer.state.y_display_unit,
                                             u.spectral_density(sp.spectral_axis))

                # Out of range in spectral axis.
                if (self.dataset.selected != lyr.layer.label and
                        (x < disp_wave.min() or x > disp_wave.max())):
                    continue

                cur_i = np.argmin(abs(disp_wave - x))
                cur_wave = disp_wave[cur_i]
                cur_flux = disp_flux[cur_i]

                dx = cur_wave - x
                dy = cur_flux - y
                cur_distance = math.sqrt(dx * dx + dy * dy)
                if (closest_distance is None) or (cur_distance < closest_distance):
                    closest_distance = cur_distance
                    closest_i = cur_i
                    closest_wave = cur_wave
                    closest_flux = cur_flux
                    closest_icon = self.app.state.layer_icons.get(lyr.layer.label, '')
                    self._dict['data_label'] = lyr.layer.label
            except Exception:  # nosec
                # Something is loaded but not the right thing
                continue

        if closest_wave is None:
            self.row2_title = '\u00A0'
            self.row2_text = ''
            self.row3_title = '\u00A0'
            self.row3_text = ''
            self.icon = 'mdi-cursor-default'
            self.marks[viewer._reference_id].visible = False
            _cursor_fallback()
            _copy_axes_to_spectral()
            return

        self.row2_title = 'Wave'
        self.row2_text = f'{closest_wave:10.5e} {viewer.state.x_display_unit}'
        self._dict['axes_x'] = closest_wave
        self._dict['axes_x:unit'] = viewer.state.x_display_unit
        if viewer.state.x_display_unit != u.pix:
            self.row2_text += f' ({int(closest_i)} pix)'
            if self.app.config == 'cubeviz':
                # float to be compatible with nan
                self._dict['slice'] = float(closest_i)
                self._dict['spectral_axis'] = closest_wave
                self._dict['spectral_axis:unit'] = viewer.state.x_display_unit
            else:
                # float to be compatible with nan
                self._dict['index'] = float(closest_i)

        if viewer.state.y_display_unit is None:
            flux_unit = ""
        else:
            flux_unit = viewer.state.y_display_unit
        self.row3_title = 'Flux'
        self.row3_text = f'{closest_flux:10.5e} {flux_unit}'
        self._dict['axes_y'] = closest_flux
        self._dict['axes_y:unit'] = viewer.state.y_display_unit

        if closest_icon is not None:
            self.icon = closest_icon
        else:
            self.icon = ""

        self.marks[viewer._reference_id].update_xy([closest_wave], [closest_flux])
        self.marks[viewer._reference_id].visible = True
        _copy_axes_to_spectral()
