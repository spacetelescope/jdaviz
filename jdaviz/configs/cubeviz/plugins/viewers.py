from functools import cached_property

from glue.core import BaseData
from glue_jupyter.bqplot.image import BqplotImageView
import numpy as np

from jdaviz.core.registries import viewer_registry
from jdaviz.configs.cubeviz.plugins.mixins import WithSliceIndicator, WithSliceSelection
from jdaviz.configs.default.plugins.viewers import JdavizViewerMixin
from jdaviz.configs.specviz.plugins.viewers import Spectrum1DViewer
from jdaviz.core.freezable_state import FreezableBqplotImageViewerState
from jdaviz.configs.cubeviz.plugins.cube_listener import MINVOL
from jdaviz.core.sonified_layers import (SonifiedDataLayerArtist,
                                         SonifiedLayerStateWidget,
                                         SonifiedLayerState)


__all__ = ['CubevizImageView', 'CubevizProfileView']


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
        self.state._set_viewer(self)

        self._subscribe_to_layers_update()
        self.state.add_callback('reference_data', self._initial_x_axis)

        self.add_event_callback(self._viewer_mouse_event, events=['mousemove',
                                                                  'mouseleave',
                                                                  'mouseenter'])

        # Hide axes by default
        self.state.show_axes = False

        self.volume_level = None

        self.data_menu._obj.dataset.add_filter('is_cube_or_image')

        self.layer_volume = {}
        self.same_pix = None
        self._cached_properties = ['combined_sonified_grid']
        self.sonified_layers_enabled = []

        self._layer_style_widget_cls[SonifiedDataLayerArtist] = SonifiedLayerStateWidget

    @property
    def _sonify_plugin(self):
        if self.jdaviz_helper is not None:
            return self.jdaviz_helper.plugins['Sonify Data']._obj
        else:
            return None

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

    @cached_property
    def combined_sonified_grid(self):

        compiled_coords = {}
        for k, v in self._sonify_plugin.data_lookup.items():
            if k not in self.sonified_layers_enabled:
                continue
            # Each (x, y) coordinate corresponds to a different sound for each layer.
            # These sounds can be combined together and played by setting cbuff to True.
            # TODO: is there a better way to combine sounds or normalize them?
            # TODO: apply 1/N or 1/N**0.5 normalisation per layer for N layers?
            for coord, sound_array in v.items():
                if coord in compiled_coords:
                    compiled_coords[coord] += ((sound_array * (int(self.layer_volume[k]) / 100)).
                                               astype(int))
                else:
                    compiled_coords[coord] = ((sound_array * (int(self.layer_volume[k]) / 100)).
                                              astype(int))
        return compiled_coords

    def recalculate_combined_sonified_grid(self, event=None):
        self.layer_volume = {}
        self.sonified_layers_enabled = []

        for layer in self.state.layers:
            if not isinstance(layer, SonifiedLayerState):
                continue

            self.layer_volume[layer.layer.label] = layer.volume
            self.sonified_layers_enabled += ([layer.layer.label] if
                                             getattr(layer, 'audible', False) else [])  # noqa

        # Need to force an update of the layer icons since
        # audible is a state attribute, not a layer artist attribute
        self.jdaviz_app.state.layer_icons.notify_all()

        if 'combined_sonified_grid' in self.__dict__:
            del self.__dict__['combined_sonified_grid']
        self.combined_sonified_grid

    def update_volume_level(self, level):
        if self._sonify_plugin is None or not self._sonify_plugin.sonified_cube:
            return
        self.volume_level = level
        self._sonify_plugin.sonified_cube.atten_level = int(1/np.clip((level/100.)**2, MINVOL, 1))

    def _viewer_mouse_event(self, data):
        if data['event'] in ('mouseleave', 'mouseenter') or not self.sonified_layers_enabled:
            self._sonify_plugin.stop_stream()
            return
        if len(self.jdaviz_app.data_collection) < 1:
            return

        # Extract data coordinates - these are pixels in the reference image
        x = np.floor(data['domain']['x'])
        y = np.floor(data['domain']['y'])

        if x is None or y is None or x < 0 or y < 0:  # Out of bounds
            return

        if self.same_pix is None:
            self.same_pix = (x, y)
        elif (x, y) == self.same_pix:
            return

        if (not self._sonify_plugin.sonified_cube or
                not hasattr(self._sonify_plugin.sonified_cube, 'newsig') or
                not hasattr(self._sonify_plugin.sonified_cube, 'sigcube')):
            return
        self._sonify_plugin.start_stream()
        self._sonify_plugin.update_sonified_cube_with_coord(self, (x, y))

    def get_data_layer_artist(self, layer=None, layer_state=None):
        if 'Sonified' in layer.meta:
            cls = SonifiedDataLayerArtist
            return self.get_layer_artist(cls, layer=layer)
        else:
            return super().get_data_layer_artist(layer, layer_state)


@viewer_registry("cubeviz-profile-viewer", label="Profile 1D (Cubeviz)")
class CubevizProfileView(Spectrum1DViewer, WithSliceIndicator):
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

    def add_subset(self, subset, *args, **kwargs):
        # The cubeviz profile viewer does not show the spectra/profiles based
        # on the subsets of the cubes, but based on extracted datasets derived
        # from those subsets. We can ignore all subsets that have a subset
        # state that was defined from the image, and we recognize these by
        # looking for subset states that are defined based on two attributes.
        if len(subset.subset_state.attributes) == 2:
            return False
        else:
            return super().add_subset(subset, *args, **kwargs)
