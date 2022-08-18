import numpy as np

from astropy.visualization import ImageNormalize, LinearStretch, PercentileInterval
from glue.core.link_helpers import LinkSame
from glue_jupyter.bqplot.image import BqplotImageView

from jdaviz.configs.imviz import wcs_utils
from jdaviz.configs.imviz.helper import data_has_valid_wcs, layer_is_image_data, get_top_layer_index
from jdaviz.core.astrowidgets_api import AstrowidgetsImageViewerMixin
from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import viewer_registry
from jdaviz.configs.default.plugins.viewers import JdavizViewerMixin

__all__ = ['ImvizImageView']


@viewer_registry("imviz-image-viewer", label="Image 2D (Imviz)")
class ImvizImageView(BqplotImageView, AstrowidgetsImageViewerMixin, JdavizViewerMixin):

    # Whether to inherit tools from glue-jupyter automatically. Set this to
    # False to have full control here over which tools are shown in case new
    # ones are added in glue-jupyter in future that we don't want here.
    inherit_tools = False

    tools = ['jdaviz:homezoom', 'jdaviz:boxzoommatch', 'jdaviz:boxzoom',
             'jdaviz:panzoommatch', 'jdaviz:imagepanzoom',
             'jdaviz:contrastbias', 'jdaviz:blinkonce',
             'bqplot:rectangle', 'bqplot:circle', 'bqplot:ellipse']

    # categories: zoom resets, zoom, pan, subset, select tools, shortcuts
    tools_nested = [
                    ['jdaviz:homezoom', 'jdaviz:prevzoom'],
                    ['jdaviz:boxzoommatch', 'jdaviz:boxzoom'],
                    ['jdaviz:panzoommatch', 'jdaviz:panzoom'],
                    ['bqplot:circle', 'bqplot:rectangle', 'bqplot:ellipse'],
                    ['jdaviz:blinkonce', 'jdaviz:contrastbias'],
                    ['jdaviz:sidebar_plot', 'jdaviz:sidebar_export', 'jdaviz:sidebar_compass']
                ]

    default_class = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_astrowidgets_api()
        self._subscribe_to_layers_update()
        self._initialize_toolbar_nested()

        self.label_mouseover = None
        self.compass = None
        self.line_profile_xy = None

        self.add_event_callback(self.on_mouse_or_key_event, events=['mousemove', 'mouseenter',
                                                                    'mouseleave', 'keydown'])
        self.state.add_callback('x_min', self.on_limits_change)
        self.state.add_callback('x_max', self.on_limits_change)
        self.state.add_callback('y_min', self.on_limits_change)
        self.state.add_callback('y_max', self.on_limits_change)

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
        visible_layers = [layer for layer in self.state.layers
                          if (layer.visible and layer_is_image_data(layer.layer))]

        if len(visible_layers) == 0:
            return

        active_layer = visible_layers[-1]

        if self.label_mouseover is None:
            if 'g-coords-info' in self.session.application._tools:
                self.label_mouseover = self.session.application._tools['g-coords-info']
            else:
                return

        if self.line_profile_xy is None:
            try:
                self.line_profile_xy = self.session.jdaviz_app.get_tray_item_from_name(
                    'imviz-line-profile-xy')
            except KeyError:  # pragma: no cover
                return

        if data['event'] == 'mousemove':
            # Display the current cursor coordinates (both pixel and world) as
            # well as data values. For now we use the first dataset in the
            # viewer for the data values.

            # Extract first dataset from visible layers and use this for coordinates - the choice
            # of dataset shouldn't matter if the datasets are linked correctly
            image = active_layer.layer
            self.label_mouseover.icon = self.jdaviz_app.state.layer_icons.get(active_layer.layer.label)  # noqa

            # Extract data coordinates - these are pixels in the reference image
            x = data['domain']['x']
            y = data['domain']['y']

            if x is None or y is None:  # Out of bounds
                self.label_mouseover.pixel = ""
                self.label_mouseover.reset_coords_display()
                self.label_mouseover.value = ""
                return

            maxsize = int(np.ceil(np.log10(np.max(image.shape)))) + 3
            fmt = 'x={0:0' + str(maxsize) + '.1f} y={1:0' + str(maxsize) + '.1f}'
            x, y, coords_status = self._get_real_xy(image, x, y)
            self.label_mouseover.pixel = (fmt.format(x, y))

            if coords_status:
                try:
                    coo = image.coords.pixel_to_world(x, y).icrs
                except Exception:  # WCS might not be celestial
                    self.label_mouseover.reset_coords_display()
                else:
                    self.label_mouseover.set_coords(coo)
            else:
                self.label_mouseover.reset_coords_display()

            # Extract data values at this position.
            # TODO: for now we just use the first visible layer but we should think
            # of how to display values when multiple datasets are present.
            if (x > -0.5 and y > -0.5
                    and x < image.shape[1] - 0.5 and y < image.shape[0] - 0.5
                    and hasattr(active_layer, 'attribute')):
                attribute = active_layer.attribute
                value = image.get_data(attribute)[int(round(y)), int(round(x))]
                unit = image.get_component(attribute).units
                self.label_mouseover.value = f'{value:+10.5e} {unit}'
            else:
                self.label_mouseover.value = ''

        elif data['event'] == 'mouseleave' or data['event'] == 'mouseenter':

            self.label_mouseover.pixel = ""
            self.label_mouseover.reset_coords_display()
            self.label_mouseover.value = ""

        elif data['event'] == 'keydown':
            key_pressed = data['key']

            if key_pressed in ('b', 'B'):
                self.blink_once(reversed=key_pressed=='B')  # noqa: E225

                # Also update the coordinates display.
                data['event'] = 'mousemove'
                self.on_mouse_or_key_event(data)

            elif key_pressed == 'l':
                # Same data as mousemove above.
                image = active_layer.layer
                x = data['domain']['x']
                y = data['domain']['y']
                if x is None or y is None:  # Out of bounds
                    return
                x, y, _ = self._get_real_xy(image, x, y)
                self.line_profile_xy.selected_x = x
                self.line_profile_xy.selected_y = y
                self.line_profile_xy.selected_viewer = self.reference_id
                self.line_profile_xy.vue_draw_plot()

    def blink_once(self, reversed=False):
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
                if not reversed:
                    delta = 1
                else:
                    delta = -1
                next_layer = valid[(valid.index(visible[-1]) + delta) % n_layers]
                self.state.layers[next_layer].visible = True

                for ilayer in (set(valid) - set([next_layer])):
                    self.state.layers[ilayer].visible = False

                # We can display the active data label in Compass plugin.
                self.set_compass(self.state.layers[next_layer].layer, transform=self.state._affine_pretransform._transform if self.state._affine_pretransform else None)

                # Update line profile plots too.
                if self.line_profile_xy is None:
                    try:
                        self.line_profile_xy = self.session.jdaviz_app.get_tray_item_from_name(
                            'imviz-line-profile-xy')
                    except KeyError:  # pragma: no cover
                        return
                self.line_profile_xy.selected_viewer = self.reference_id
                self.line_profile_xy.vue_draw_plot()

    def on_limits_change(self, *args):
        try:
            i = get_top_layer_index(self)
        except IndexError:
            if self.compass is not None:
                self.compass.clear_compass()
            return
        self.set_compass(self.state.layers[i].layer, transform=self.state._affine_pretransform._transform if self.state._affine_pretransform else None)

    def _get_real_xy(self, image, x, y):
        """Return real (X, Y) position and status in case of dithering.

        ``coords_status`` is for ``self.label_mouseover`` coords handling only.
        When `True`, it sets the coords, otherwise it resets.

        """
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
                coords_status = True
            except Exception:
                coords_status = False
        else:
            coords_status = False

        return x, y, coords_status

    def _get_zoom_limits(self, image):
        """Return a list of ``(x, y)`` that defines four corners of
        the zoom box for a given image.
        This is needed because viewer values are only based on reference
        image, which can be inaccurate if given image is dithered and
        they are linked by WCS.
        """
        if data_has_valid_wcs(image) and self.get_link_type(image.label) == 'wcs':
            # Convert X,Y from reference data to the one we are actually seeing.
            x = image.coords.world_to_pixel(self.state.reference_data.coords.pixel_to_world(
                (self.state.x_min, self.state.x_min, self.state.x_max, self.state.x_max),
                (self.state.y_min, self.state.y_max, self.state.y_max, self.state.y_min)))
            zoom_limits = np.array(list(zip(x[0], x[1])))
        else:
            zoom_limits = np.array(((self.state.x_min, self.state.y_min),
                                    (self.state.x_min, self.state.y_max),
                                    (self.state.x_max, self.state.y_max),
                                    (self.state.x_max, self.state.y_min)))
        return zoom_limits

    def set_compass(self, image, transform=None):
        """Update the Compass plugin with info from the given image Data object."""
        if self.compass is None:  # Maybe another viewer has it
            return

        zoom_limits = self._get_zoom_limits(image)

        # Downsample input data to about 400px (as per compass.vue) for performance.
        xstep = max(1, round(image.shape[1] / 400))
        ystep = max(1, round(image.shape[0] / 400))
        arr = image[image.main_components[0]][::ystep, ::xstep]
        vmin, vmax = PercentileInterval(95).get_limits(arr)
        norm = ImageNormalize(vmin=vmin, vmax=vmax, stretch=LinearStretch())
        self.compass.draw_compass(image.label, wcs_utils.draw_compass_mpl(
            arr, orig_shape=image.shape, wcs=image.coords, show=False, zoom_limits=zoom_limits,
            norm=norm, transform=transform))

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
