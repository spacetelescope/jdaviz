from glue.core import BaseData
from glue_jupyter.bqplot.image import BqplotImageView

from bqplot import Label

from jdaviz.core.registries import viewer_registry

__all__ = ['ImVizImageView']


@viewer_registry("imviz-image-viewer", label="Image 2D (ImViz)")
class ImVizImageView(BqplotImageView):

    tools = ['bqplot:panzoom', 'bqplot:rectangle', 'bqplot:circle', 'bqplot:matchwcs']

    default_class = None

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.label_mouseover = Label(x=[0.05], y=[0.05], text=[''],
                                     default_size=12, colors=['orange'])
        self.figure.marks = self.figure.marks + [self.label_mouseover]

        self.add_event_callback(self.on_mouse_or_key_event)

    def on_mouse_or_key_event(self, data):

        if data['event'] == 'mousemove':

            # Display the current cursor coordinates (both pixel and world) as
            # well as data values. For now we use the first dataset in the
            # viewer for the data values.

            # Extract data coordinates - these are pixels in the image
            x = data['domain']['x']
            y = data['domain']['y']

            overlay = f'x={x:.1f} y={y:.1f}'

            image = self.state.layers[0].layer

            # Convert these to a SkyCoord via WCS - note that for other datasets
            # we aren't actually guaranteed to get a SkyCoord out, just for images
            # with valid celestial WCS
            celestial_coordinates = image.coords.pixel_to_world(x, y).icrs.to_string('hmsdms')
            overlay += f' ICRS={celestial_coordinates}'

            # Extract data values at this position
            if x > -0.5 and y > -0.5 and x < image.shape[1] and y < image.shape[0]:
                value = image.get_data(image.main_components[0])[int(round(y)), int(round(x))]
                overlay += f' data={value:.2g}'

            self.label_mouseover.text = [overlay]

        elif data['event'] == 'mouseleave' or data['event'] == 'mouseenter':

            self.label_mouseover.text = ""

        if data['event'] == 'keydown' and data['key'] == 'b':

            # Simple blinking of images - this will make it so that only one
            # layer is visible at a time and cycles through the layers.

            if len(self.state.layers) > 1:

                # If only one layer is visible, pick the next one to be visible,
                # otherwise start from the last visible one.

                visible = [ilayer for ilayer, layer in
                           enumerate(self.state.layers) if layer.visible]

                if len(visible) > 0:
                    next_layer = (visible[-1] + 1) % len(self.state.layers)
                    self.state.layers[next_layer].visible = True
                    for ilayer in visible:
                        if ilayer != next_layer:
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
