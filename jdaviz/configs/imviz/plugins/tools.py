from bqplot import Label
from bqplot_image_gl.interacts import MouseInteraction
from glue.config import viewer_tool
from glue_jupyter.bqplot.common.tools import InteractCheckableTool

__all__ = []


@viewer_tool
class BqplotCoordsOverlay(InteractCheckableTool):

    # TODO: This class should be moved 'up' into glue-jupyter - however at the
    # moment it is specific to celestial WCSes, so this would need to be
    # generalized, potentially providing hooks to register custom formatting
    # functions. In addition at the moment it will show the data value from the
    # first layer, so we should figure out how we want this to behave when
    # multiple layers are present, sometimes with some degree of transparency
    # between layers.

    # TODO: design a custom icon for this tool
    icon = 'glue_crosshair'
    tool_id = 'bqplot:coords'
    action_text = 'Show cursor overlay'
    tool_tip = 'Move cursor on image to see coordinates and data overlay'

    def __init__(self, viewer, **kwargs):

        super().__init__(viewer, **kwargs)

        self.label = Label(x=[0.05], y=[0.05], text=[''], default_size=12, colors=['orange'])
        viewer.figure.marks = viewer.figure.marks + [self.label]

        self.interact = MouseInteraction(x_scale=viewer.figure.axes[0].scale,
                                         y_scale=viewer.figure.axes[1].scale, move_throttle=70)
        self.interact.on_msg(self.on_event)

    def on_event(self, interaction, data, buffers):

        # For now use the first dataset in the viewer
        # FIXME: decide how to generalize this
        image = self.viewer.state.layers[0].layer

        # Extract data coordinates - these are pixels in the image
        x = data['domain']['x']
        y = data['domain']['y']

        overlay = f'x={x:.1f} y={y:.1f}'

        # Convert these to a SkyCoord via WCS - note that for other datasets
        # we aren't actually guaranteed to get a SkyCoord out, just for images
        # with valid celestial WCS
        celestial_coordinates = image.coords.pixel_to_world(x, y).icrs.to_string('hmsdms')
        overlay += f' ICRS={celestial_coordinates}'

        # Extract data values at this position
        if x > -0.5 and y > -0.5 and x < image.shape[1] and y < image.shape[0]:
            value = image.get_data(image.main_components[0])[int(round(y)), int(round(x))]
            overlay += f' data={value:.2g}'

        # For now we just show the coordinates but it would be easy to show the data
        # values for one or more of the images

        if data['event'] == 'mousemove':
            self.label.text = [overlay]
        elif data['event'] == 'mouseleave':
            self.label.text = ""
        elif data['event'] == 'mouseenter':
            self.label.text = ""

