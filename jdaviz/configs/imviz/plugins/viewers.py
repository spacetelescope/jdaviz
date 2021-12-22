import numpy as np

from glue.core.link_helpers import LinkSame
from glue_jupyter.bqplot.image import BqplotImageView

from jdaviz.configs.imviz.helper import data_has_valid_wcs, layer_is_image_data
from jdaviz.core.astrowidgets_api import AstrowidgetsImageViewerMixin
from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import viewer_registry

__all__ = ['ImvizImageView']


@viewer_registry("imviz-image-viewer", label="Image 2D (Imviz)")
class ImvizImageView(BqplotImageView, AstrowidgetsImageViewerMixin):

    # Whether to inherit tools from glue-jupyter automatically. Set this to
    # False to have full control here over which tools are shown in case new
    # ones are added in glue-jupyter in future that we don't want here.
    inherit_tools = False

    tools = ['bqplot:home', 'jdaviz:boxzoom', 'jdaviz:boxzoommatch',
             'bqplot:panzoom', 'jdaviz:panzoommatch',
             'jdaviz:contrastbias', 'jdaviz:blinkonce',
             'bqplot:rectangle', 'bqplot:circle', 'bqplot:ellipse']
    default_class = None

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.init_astrowidgets_api()

        self.label_mouseover = None

        self.add_event_callback(self.on_mouse_or_key_event, events=['mousemove', 'mouseenter',
                                                                    'mouseleave', 'keydown'])

        self.state.show_axes = False
        self.figure.fig_margin = {'left': 0, 'bottom': 0, 'top': 0, 'right': 0}

        # By default, glue computes a fixed resolution buffer that matches the
        # axes - but this means that when panning, one sees white outside of
        # the original buffer until the buffer updates again, thus there is a
        # lag in the image display. By increasing the external padding to 0.5
        # the image is made larger by 50% along all four sides, helping create
        # the illusion of smooth panning. We can increase this further to
        # improve the panning experience, but this can cause a larger delay
        # when the image does need to update as it will be more computationally
        # intensive.
        self.state.image_external_padding = 0.5

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
                self.label_mouseover.reset_coords_display()
                self.label_mouseover.value = ""
                return

            maxsize = int(np.ceil(np.log10(np.max(image.shape)))) + 3
            fmt = 'x={0:0' + str(maxsize) + '.1f} y={1:0' + str(maxsize) + '.1f}'

            if data_has_valid_wcs(image):
                # Convert these to a SkyCoord via WCS - note that for other datasets
                # we aren't actually guaranteed to get a SkyCoord out, just for images
                # with valid celestial WCS
                try:
                    # Convert X,Y from reference data to the one we are actually seeing.
                    # world_to_pixel return scalar ndarray that we need to convert to float.
                    if self.get_link_type(image.label) == 'wcs':
                        x, y = list(map(float, image.coords.world_to_pixel(
                            self.state.reference_data.coords.pixel_to_world(x, y))))

                    self.label_mouseover.pixel = (fmt.format(x, y))
                    coo = image.coords.pixel_to_world(x, y).icrs
                    self.label_mouseover.set_coords(coo)
                except Exception:
                    self.label_mouseover.pixel = (fmt.format(x, y))
                    self.label_mouseover.reset_coords_display()
            else:
                self.label_mouseover.pixel = (fmt.format(x, y))
                self.label_mouseover.reset_coords_display()

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
            self.label_mouseover.reset_coords_display()
            self.label_mouseover.value = ""

        elif data['event'] == 'keydown' and data['key'] == 'b':
            self.blink_once()

            # Also update the coordinates display.
            data['event'] = 'mousemove'
            self.on_mouse_or_key_event(data)

    def blink_once(self):
        # Simple blinking of images - this will make it so that only one
        # layer is visible at a time and cycles through the layers.

        # Exclude Subsets: They are global
        valid = [ilayer for ilayer, layer in enumerate(self.state.layers)
                 if layer_is_image_data(layer.layer)]
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

                # TODO: We can display the active data label in GUI here.
                # For now, we will print to debug Output widget.
                data_label = self.state.layers[next_layer].layer.label
                with self.session.application.output:
                    print(f'Visible layer changed to: {data_label}')

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
                layer_is_image_data(layer_state.layer)]

    def get_link_type(self, data_label):
        """Find the type of ``glue`` linking between the given
        data label with the reference data in viewer.

        Parameters
        ----------
        data_label : str
            Data label to look up.

        Returns
        -------
        link_type : {'pixels', 'wcs', 'self'}
            One of the link types accepted by :func:`~jdaviz.configs.imviz.helper.link_image_data`
            or ``'self'`` if the data label belongs to the reference data itself.

        Raises
        ------
        ValueError
            Link look-up failed.

        """
        if self.state.reference_data is None:
            raise ValueError('No reference data for link look-up')

        ref_label = self.state.reference_data.label
        if data_label == ref_label:
            return 'self'

        link_type = None
        for elink in self.session.application.data_collection.external_links:
            elink_labels = (elink.data1.label, elink.data2.label)
            if data_label in elink_labels and ref_label in elink_labels:
                if isinstance(elink, LinkSame):  # Assumes WCS link never uses LinkSame
                    link_type = 'pixels'
                else:  # If not pixels, must be WCS
                    link_type = 'wcs'
                break  # Might have duplicate, just grab first match

        if link_type is None:
            raise ValueError(f'{data_label} not found in data collection external links')

        return link_type
