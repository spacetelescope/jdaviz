import numpy as np
from glue.core import BaseData
from glue_jupyter.bqplot.image import BqplotImageView

from jdaviz.core.registries import viewer_registry
from jdaviz.core.marks import SliceIndicatorMarks
from jdaviz.configs.default.plugins.viewers import JdavizViewerMixin
from jdaviz.configs.imviz.helper import data_has_valid_wcs
from jdaviz.configs.specviz.plugins.viewers import SpecvizProfileView

__all__ = ['CubevizImageView', 'CubevizProfileView']


@viewer_registry("cubeviz-image-viewer", label="Image 2D (Cubeviz)")
class CubevizImageView(BqplotImageView, JdavizViewerMixin):
    # Whether to inherit tools from glue-jupyter automatically. Set this to
    # False to have full control here over which tools are shown in case new
    # ones are added in glue-jupyter in future that we don't want here.
    inherit_tools = False

    tools = ['jdaviz:homezoom', 'jdaviz:boxzoom',
             'jdaviz:panzoom', 'bqplot:rectangle',
             'bqplot:circle', 'jdaviz:spectrumperspaxel']

    # categories: zoom resets, (zoom, pan), subset, select tools, shortcuts
    # NOTE: zoom and pan are merged here for space consideration and to avoid
    # overflow to second row when opening the tray
    tools_nested = [
                    ['jdaviz:homezoom', 'jdaviz:prevzoom'],
                    ['jdaviz:boxzoom', 'jdaviz:panzoom'],
                    ['bqplot:circle', 'bqplot:rectangle'],
                    ['jdaviz:spectrumperspaxel'],
                    ['jdaviz:sidebar_plot', 'jdaviz:sidebar_export']
                ]

    default_class = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._subscribe_to_layers_update()
        self._initialize_toolbar_nested()
        self.state.add_callback('reference_data', self._initial_x_axis)

        self.label_mouseover = None
        self.add_event_callback(self.on_mouse_or_key_event, events=['mousemove', 'mouseenter',
                                                                    'mouseleave'])

    def on_mouse_or_key_event(self, data):

        # Find visible layers
        visible_layers = [layer for layer in self.state.layers if layer.visible]

        if len(visible_layers) == 0:
            return

        if self.label_mouseover is None:
            if 'g-coords-info' in self.session.application._tools:
                self.label_mouseover = self.session.application._tools['g-coords-info']
            else:
                return

        if data['event'] == 'mousemove':
            # Display the current cursor coordinates (both pixel and world) as
            # well as data values. For now we use the first dataset in the
            # viewer for the data values.

            # Extract first dataset from visible layers and use this for coordinates - the choice
            # of dataset shouldn't matter if the datasets are linked correctly
            active_layer = visible_layers[-1]
            image = active_layer.layer

            # Extract data coordinates - these are pixels in the reference image
            x = data['domain']['x']
            y = data['domain']['y']

            if x is None or y is None:  # Out of bounds
                self.label_mouseover.pixel = ""
                self.label_mouseover.reset_coords_display()
                self.label_mouseover.value = ""
                return

            maxsize = int(np.ceil(np.log10(np.max(image.shape[:2])))) + 3
            fmt = 'x={0:0' + str(maxsize) + '.1f} y={1:0' + str(maxsize) + '.1f}'
            self.label_mouseover.pixel = (fmt.format(x, y))

            if data_has_valid_wcs(image):
                try:
                    coo = image.coords.pixel_to_world(x, y, self.state.slices[-1])[-1].icrs
                except Exception:
                    self.label_mouseover.reset_coords_display()
                else:
                    self.label_mouseover.set_coords(coo)
            else:
                self.label_mouseover.reset_coords_display()

            # Extract data values at this position.
            # Check if shape is [x, y, z] or [x, y] and show value accordingly.
            if (-0.5 < x < image.shape[0] - 0.5 and -0.5 < y < image.shape[1] - 0.5
                    and hasattr(active_layer, 'attribute')):
                attribute = active_layer.attribute
                if len(image.shape) == 3:
                    value = image.get_data(attribute)[int(round(x)), int(round(y)),
                                                      self.state.slices[-1]]
                elif len(image.shape) == 2:
                    value = image.get_data(attribute)[int(round(x)), int(round(y))]

                unit = image.get_component(attribute).units
                self.label_mouseover.value = f'{value:+10.5e} {unit}'
            else:
                self.label_mouseover.value = ''

        elif data['event'] == 'mouseleave' or data['event'] == 'mouseenter':

            self.label_mouseover.pixel = ""
            self.label_mouseover.reset_coords_display()
            self.label_mouseover.value = ""

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


@viewer_registry("cubeviz-profile-viewer", label="Profile 1D (Cubeviz)")
class CubevizProfileView(SpecvizProfileView):
    # Whether to inherit tools from glue-jupyter automatically. Set this to
    # False to have full control here over which tools are shown in case new
    # ones are added in glue-jupyter in future that we don't want here.
    inherit_tools = False

    tools = ['jdaviz:homezoom',
             'jdaviz:boxzoom', 'jdaviz:xrangezoom',
             'jdaviz:panzoom', 'jdaviz:panzoom_x',
             'jdaviz:panzoom_y', 'bqplot:xrange',
             'jdaviz:selectslice', 'jdaviz:selectline']

    # categories: zoom resets, zoom, pan, subset, select tools, shortcuts
    tools_nested = [
                    ['jdaviz:homezoom', 'jdaviz:prevzoom'],
                    ['jdaviz:boxzoom', 'jdaviz:xrangezoom'],
                    ['jdaviz:panzoom', 'jdaviz:panzoom_x', 'jdaviz:panzoom_y'],
                    ['bqplot:xrange'],
                    ['jdaviz:selectslice', 'jdaviz:selectline'],
                    ['jdaviz:sidebar_plot', 'jdaviz:sidebar_export']
                ]

    def __init__(self, *args, **kwargs):
        # NOTE: super will initialize nested toolbar with
        # default_tool_priority=['jdaviz:selectslice']
        super().__init__(*args, **kwargs)

    @property
    def slice_indicator(self):
        for mark in self.figure.marks:
            if isinstance(mark, SliceIndicatorMarks):
                return mark

        # SliceIndicatorMarks does not yet exist
        slice_indicator = SliceIndicatorMarks(self)
        self.figure.marks = self.figure.marks + slice_indicator.marks
        return slice_indicator

    def _update_slice_indicator(self, slice):
        self.slice_indicator.slice = slice
