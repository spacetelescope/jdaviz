import numpy as np

from astropy.wcs.wcsapi import BaseHighLevelWCS

from glue.core import BaseData
from glue_jupyter.bqplot.image import BqplotImageView

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import viewer_registry

__all__ = ['ImvizImageView']


@viewer_registry("imviz-image-viewer", label="Image 2D (Imviz)")
class ImvizImageView(BqplotImageView):

    # Whether to inherit tools from glue-jupyter automatically. Set this to
    # False to have full control here over which tools are shown in case new
    # ones are added in glue-jupyter in future that we don't want here.
    inherit_tools = False

    tools = ['bqplot:home', 'bqplot:panzoom', 'bqplot:panzoomwcs',
             'bqplot:contrastbias', 'bqplot:blinkonce',
             'bqplot:rectangle', 'bqplot:circle']
    default_class = None

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.label_mouseover = None

        self.add_event_callback(self.on_mouse_or_key_event, events=['mousemove', 'mouseenter',
                                                                    'mouseleave', 'keydown'])

        self.state.show_axes = False

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
            image = visible_layers[0].layer

            # Extract data coordinates - these are pixels in the image
            x = data['domain']['x']
            y = data['domain']['y']

            if x is None or y is None:  # Out of bounds
                self.label_mouseover.pixel = ""
                self.label_mouseover.world = ""
                self.label_mouseover.value = ""
                return

            maxsize = int(np.ceil(np.log10(np.max(image.shape)))) + 3

            fmt = 'x={0:0' + str(maxsize) + '.1f} y={1:0' + str(maxsize) + '.1f}'

            self.label_mouseover.pixel = (fmt.format(x, y))

            if hasattr(image, 'coords') and isinstance(image.coords, BaseHighLevelWCS):
                # Convert these to a SkyCoord via WCS - note that for other datasets
                # we aren't actually guaranteed to get a SkyCoord out, just for images
                # with valid celestial WCS
                try:
                    celestial_coordinates = (image.coords.pixel_to_world(x, y).icrs
                                             .to_string('hmsdms', precision=4, pad=True))
                except Exception:
                    self.label_mouseover.world = ''
                else:
                    self.label_mouseover.world = f'{celestial_coordinates:32s} (ICRS)'
            else:
                self.label_mouseover.world = ''

            # Extract data values at this position.
            # TODO: for now we just use the first visible layer but we should think
            # of how to display values when multiple datasets are present.
            if (x > -0.5 and y > -0.5
                    and x < image.shape[1] - 0.5 and y < image.shape[0] - 0.5
                    and hasattr(visible_layers[0], 'attribute')):
                attribute = visible_layers[0].attribute
                value = image.get_data(attribute)[int(round(y)), int(round(x))]
                unit = image.get_component(attribute).units
                self.label_mouseover.value = f'{value:+10.5e} {unit}'
            else:
                self.label_mouseover.value = ''

        elif data['event'] == 'mouseleave' or data['event'] == 'mouseenter':

            self.label_mouseover.pixel = ""
            self.label_mouseover.world = ""
            self.label_mouseover.value = ""

        elif data['event'] == 'keydown' and data['key'] == 'b':
            self.blink_once()

    def blink_once(self):
        # Simple blinking of images - this will make it so that only one
        # layer is visible at a time and cycles through the layers.

        # Exclude Subsets: They are global
        valid = [ilayer for ilayer, layer in enumerate(self.state.layers)
                 if isinstance(layer.layer, BaseData)]
        n_layers = len(valid)

        if n_layers == 1:
            msg = SnackbarMessage(
                'Nothing to blink. Select a second image in the Data menu to use this feature.',
                color='warning', sender=self)
            self.session.hub.broadcast(msg)

        elif n_layers > 1:
            # If only one layer is visible, pick the next one to be visible,
            # otherwise start from the last visible one.

            visible = [ilayer for ilayer in valid if self.state.layers[ilayer].visible]
            n_visible = len(visible)

            if n_visible == 0:
                msg = SnackbarMessage('No visible layer to blink',
                                      color='warning', sender=self)
                self.session.hub.broadcast(msg)
            elif n_visible > 0:
                next_layer = valid[(valid.index(visible[-1]) + 1) % n_layers]
                self.state.layers[next_layer].visible = True
                for ilayer in (set(valid) - set([next_layer])):
                    self.state.layers[ilayer].visible = False

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
