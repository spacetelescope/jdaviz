import numpy as np
import astropy.units as u
from functools import cached_property
from glue.core import BaseData
from glue_jupyter.bqplot.image import BqplotImageView

from jdaviz.core.registries import viewer_registry
from jdaviz.core.marks import SliceIndicatorMarks
from jdaviz.configs.default.plugins.viewers import JdavizViewerMixin
from jdaviz.configs.specviz.plugins.viewers import SpecvizProfileView
from jdaviz.core.freezable_state import FreezableBqplotImageViewerState

from jdaviz.configs.cubeviz.plugins.cube_listener import CubeListenerData
import sounddevice as sd

__all__ = ['CubevizImageView', 'CubevizProfileView',
           'WithSliceIndicator', 'WithSliceSelection']


class WithSliceIndicator:
    @property
    def slice_component_label(self):
        return str(self.state.x_att)

    @property
    def slice_display_unit_name(self):
        return 'spectral'

    @cached_property
    def slice_indicator(self):
        # SliceIndicatorMarks does not yet exist
        slice_indicator = SliceIndicatorMarks(self)
        self.figure.marks = self.figure.marks + slice_indicator.marks
        return slice_indicator

    @property
    def slice_values(self):
        # NOTE: these are cached at the slice-plugin level
        # Retrieve display units
        slice_display_units = self.jdaviz_app._get_display_unit(
            self.slice_display_unit_name
        )

        def _get_component(layer):
            try:
                # Retrieve layer data and units
                data_comp = layer.layer.data.get_component(self.slice_component_label)
            except (AttributeError, KeyError):
                # layer either does not have get_component (because its a subset)
                # or slice_component_label is not a component in this layer
                # either way, return an empty array and skip this layer
                return np.array([])

            # Convert axis if display units are set and are different
            data_units = getattr(data_comp, 'units', None)
            if slice_display_units and data_units and slice_display_units != data_units:
                data = np.asarray(data_comp.data, dtype=float) * u.Unit(data_units)
                return data.to_value(slice_display_units,
                                     equivalencies=u.spectral())
            else:
                return data_comp.data
        try:
            return np.asarray(np.unique(np.concatenate([_get_component(layer) for layer in self.layers])),  # noqa
                              dtype=float)
        except ValueError:
            # NOTE: this will result in caching an empty list
            return np.array([])

    def _set_slice_indicator_value(self, value):
        # this is a separate method so that viewers can override and map value if necessary
        # NOTE: on first call, this will initialize the indicator itself
        self.slice_indicator.value = value


class WithSliceSelection:
    @property
    def slice_index(self):
        # index in state.slices corresponding to the slice axis
        return 2

    @property
    def slice_component_label(self):
        slice_plg = self.jdaviz_helper.plugins.get('Slice', None)
        if slice_plg is None:  # pragma: no cover
            raise ValueError("slice plugin must be activated to access slice_component_label")
        return slice_plg._obj.slice_indicator_viewers[0].slice_component_label

    @property
    def slice_display_unit_name(self):
        return 'spectral'

    @property
    def slice_values(self):
        # NOTE: these are cached at the slice-plugin level
        # TODO: add support for multiple cubes (but then slice selection needs to be more complex)
        # if slice_index is 0, then we want the equivalent of [:, 0, 0]
        # if slice_index is 1, then we want the equivalent of [0, :, 0]
        # if slice_index is 2, then we want the equivalent of [0, 0, :]
        take_inds = [2, 1, 0]
        take_inds.remove(self.slice_index)
        converted_axis = np.array([])
        for layer in self.layers:
            world_comp_ids = layer.layer.data.world_component_ids
            if self.slice_index >= len(world_comp_ids):
                # Case where 2D image is loaded in image viewer
                continue

            # Retrieve display units
            slice_display_units = self.jdaviz_app._get_display_unit(
                self.slice_display_unit_name
            )

            try:
                # Retrieve layer data and units using the slice index of the world components ids
                data_comp = layer.layer.data.get_component(world_comp_ids[self.slice_index])
            except (AttributeError, KeyError):
                continue

            data = np.asarray(data_comp.data.take(0, take_inds[0]).take(0, take_inds[1]),  # noqa
                              dtype=float)

            # Convert to display units if applicable
            data_units = getattr(data_comp, 'units', None)
            if slice_display_units and data_units and slice_display_units != data_units:
                converted_axis = (data * u.Unit(data_units)).to_value(
                    slice_display_units,
                    equivalencies=u.spectral() + u.pixel_scale(1*u.pix)
                )
            else:
                converted_axis = data

        return converted_axis

    @property
    def slice(self):
        return self.state.slices[self.slice_index]

    @slice.setter
    def slice(self, slice):
        # NOTE: not intended for user-access - this should be controlled through the slice plugin
        # in order to sync with all other viewers/slice indicators
        slices = [0, 0, 0]
        slices[self.slice_index] = slice
        self.state.slices = tuple(slices)

    @property
    def slice_value(self):
        return self.slice_values[self.slice]

    @slice_value.setter
    def slice_value(self, slice_value):
        # NOTE: not intended for user-access - this should be controlled through the slice plugin
        # in order to sync with all other viewers/slice indicators
        # find the slice nearest slice_value
        slice_values = self.slice_values
        if not len(slice_values):
            return
        self.slice = np.argmin(abs(slice_values - slice_value))


@viewer_registry("cubeviz-image-viewer", label="Image 2D (Cubeviz)")
class CubevizImageView(JdavizViewerMixin, WithSliceSelection, BqplotImageView):
    # categories: zoom resets, (zoom, pan), subset, select tools, shortcuts
    # NOTE: zoom and pan are merged here for space consideration and to avoid
    # overflow to second row when opening the tray
    tools_nested = [
                    ['jdaviz:homezoom', 'jdaviz:prevzoom'],
                    ['jdaviz:pixelboxzoommatch', 'jdaviz:boxzoom',
                     'jdaviz:pixelpanzoommatch', 'jdaviz:panzoom'],
                    ['bqplot:truecircle', 'bqplot:rectangle', 'bqplot:ellipse',
                     'bqplot:circannulus'],
                    ['jdaviz:spectrumperspaxel'],
                    ['jdaviz:sidebar_plot', 'jdaviz:sidebar_export']
                ]

    default_class = None
    _state_cls = FreezableBqplotImageViewerState

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # provide reference from state back to viewer to use for zoom syncing
        self.state._viewer = self

        self._subscribe_to_layers_update()
        self.state.add_callback('reference_data', self._initial_x_axis)

        # Hide axes by default
        self.state.show_axes = False

        self.audified_cube = None
        self.stream = None

    @property
    def _default_spectrum_viewer_reference_name(self):
        return self.jdaviz_helper._default_spectrum_viewer_reference_name

    @property
    def _default_flux_viewer_reference_name(self):
        return self.jdaviz_helper._default_flux_viewer_reference_name

    @property
    def _default_uncert_viewer_reference_name(self):
        return self.jdaviz_helper._default_uncert_viewer_reference_name

    def _initial_x_axis(self, *args):
        # Make sure that the x_att is correct on data load
        ref_data = self.state.reference_data
        if ref_data and ref_data.ndim == 3:
            for att_name in ["Right Ascension", "RA", "Galactic Longitude"]:
                if att_name in ref_data.component_ids():
                    x_att = att_name
                    self.state.x_att_world = ref_data.id[x_att]
                    break
            else:
                x_att = "Pixel Axis 0 [z]"
                self.state.x_att = ref_data.id[x_att]

    def set_plot_axes(self):
        self.figure.axes[1].tick_format = None
        self.figure.axes[0].tick_format = None

        self.figure.axes[1].label = "y: pixels"
        self.figure.axes[0].label = "x: pixels"

        # Make it so y axis label is not covering tick numbers.
        self.figure.axes[1].label_offset = "-50"

    def data(self, cls=None):
        return [layer_state.layer  # .get_object(cls=cls or self.default_class)
                for layer_state in self.state.layers
                if hasattr(layer_state, 'layer') and
                isinstance(layer_state.layer, BaseData)]

    def start_stream(self):
        if self.stream:
            self.stream.start()

    def stop_stream(self):
        if self.stream:
            self.stream.stop()

    def update_cube(self, x, y):
        if not self.audified_cube or not hasattr(self.audified_cube, 'newsig') or not hasattr(self.audified_cube, 'sigcube'):
            return
        self.audified_cube.newsig = self.audified_cube.sigcube[x, y, :]
        self.audified_cube.cbuff = True

    def get_sonified_cube(self, sample_rate, buffer_size, assidx, ssvidx, pccut):
        spectrum = self.active_image_layer.layer.get_object(statistic=None)
        pc_cube = np.percentile(np.nan_to_num(spectrum.flux.value), np.clip(pccut,0,99), axis=-1)

        # clip zeros and remove NaNs
        clipped_arr = np.nan_to_num(np.clip(spectrum.flux.value, 0, np.inf), copy=False)

        # make a rough white-light image from the clipped array
        whitelight = np.expand_dims(clipped_arr.sum(-1), axis=2)

        # subtract any percentile cut
        clipped_arr -= np.expand_dims(pc_cube, axis=2)

        # and re-clip
        clipped_arr = np.clip(clipped_arr, 0, np.inf)
        
        self.audified_cube = CubeListenerData(clipped_arr ** assidx, spectrum.wavelength.value, duration=0.8,
                                  samplerate=sample_rate, buffsize=buffer_size)
        self.audified_cube.audify_cube()
        self.audified_cube.sigcube = (self.audified_cube.sigcube * pow(whitelight / whitelight.max(), ssvidx)).astype('int16')
        self.stream = sd.OutputStream(samplerate=sample_rate, blocksize=buffer_size, channels=1, dtype='int16', latency='low',
                                      callback=self.audified_cube.player_callback)
        self.audified_cube.cbuff = True


@viewer_registry("cubeviz-profile-viewer", label="Profile 1D (Cubeviz)")
class CubevizProfileView(SpecvizProfileView, WithSliceIndicator):
    # categories: zoom resets, zoom, pan, subset, select tools, shortcuts
    tools_nested = [
                    ['jdaviz:homezoom', 'jdaviz:prevzoom'],
                    ['jdaviz:boxzoom', 'jdaviz:xrangezoom', 'jdaviz:yrangezoom'],
                    ['jdaviz:panzoom', 'jdaviz:panzoom_x', 'jdaviz:panzoom_y'],
                    ['bqplot:xrange'],
                    ['jdaviz:selectslice', 'jdaviz:selectline'],
                    ['jdaviz:sidebar_plot', 'jdaviz:sidebar_export']
                ]

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('default_tool_priority', ['jdaviz:selectslice'])
        super().__init__(*args, **kwargs)

    @property
    def _default_flux_viewer_reference_name(self):
        return self.jdaviz_helper._default_flux_viewer_reference_name
