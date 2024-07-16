import numpy as np

import astropy.units as u
from astropy.wcs.utils import pixel_to_pixel
from astropy.visualization import ImageNormalize, LinearStretch, PercentileInterval
from glue.core.link_helpers import LinkSame
from glue_jupyter.bqplot.image import BqplotImageView

from jdaviz.configs.imviz import wcs_utils
from jdaviz.configs.imviz.helper import layer_is_image_data, get_top_layer_index
from jdaviz.core.astrowidgets_api import AstrowidgetsImageViewerMixin
from jdaviz.core.events import SnackbarMessage
from jdaviz.core.helpers import data_has_valid_wcs
from jdaviz.core.registries import viewer_registry
from jdaviz.core.freezable_state import FreezableBqplotImageViewerState
from jdaviz.configs.default.plugins.viewers import JdavizViewerMixin

from astropy.table import Table
from glue.core.subset import Subset
from glue.config import data_translator
from glue.core import BaseData
from glue.core.exceptions import IncompatibleAttribute
from glue.core.roi import RangeROI
from glue.core.subset_group import GroupedSubset
from glue.viewers.scatter.state import ScatterViewerState as GlueScatterViewerState

from glue_jupyter.bqplot.scatter import BqplotScatterView
from jdaviz.configs.specviz.plugins.viewers import SpecvizProfileView
from jdaviz.configs.imviz.plugins.parsers import component_ids


__all__ = ['ImvizImageView']


@viewer_registry("imviz-image-viewer", label="Image 2D (Imviz)")
class ImvizImageView(JdavizViewerMixin, BqplotImageView, AstrowidgetsImageViewerMixin):
    # categories: zoom resets, zoom, pan, subset, select tools, shortcuts
    tools_nested = [
                    ['jdaviz:homezoom', 'jdaviz:prevzoom'],
                    ['jdaviz:boxzoommatch', 'jdaviz:boxzoom'],
                    ['jdaviz:panzoommatch', 'jdaviz:imagepanzoom'],
                    ['bqplot:truecircle', 'bqplot:rectangle', 'bqplot:ellipse',
                     'bqplot:circannulus'],
                    ['jdaviz:blinkonce', 'jdaviz:contrastbias'],
                    ['jdaviz:sidebar_plot', 'jdaviz:sidebar_export', 'jdaviz:sidebar_compass']
                ]

    default_class = None
    _state_cls = FreezableBqplotImageViewerState

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # provide reference from state back to viewer to use for zoom syncing
        self.state._viewer = self
        self.init_astrowidgets_api()
        self._subscribe_to_layers_update()

        self.compass = None
        self.line_profile_xy = None

        self.add_event_callback(self.on_mouse_or_key_event, events=['keydown'])
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
        active_image_layer = self.active_image_layer
        if active_image_layer is None:
            return

        if self.line_profile_xy is None:
            try:
                self.line_profile_xy = self.session.jdaviz_app.get_tray_item_from_name(
                    'imviz-line-profile-xy')
            except KeyError:  # pragma: no cover
                return

        if data['event'] == 'keydown':
            key_pressed = data['key']

            if key_pressed in ('b', 'B'):
                self.blink_once(reversed=key_pressed=='B')  # noqa: E225

    def blink_once(self, reversed=False):
        # Simple blinking of images - this will make it so that only one
        # layer is visible at a time and cycles through the layers.

        # Exclude Subsets (they are global) and children via associated data

        def is_parent(data):
            return self.session.jdaviz_app._get_assoc_data_parent(data.label) is None

        valid = [ilayer for ilayer, layer in enumerate(self.state.layers)
                 if layer_is_image_data(layer.layer) and is_parent(layer.layer)]
        children = [ilayer for ilayer, layer in enumerate(self.state.layers)
                    if layer_is_image_data(layer.layer) and not is_parent(layer.layer)]

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

                # make invisible all parent layers other than the next layer:
                layers_to_set_not_visible = set(valid) - set([next_layer])
                # no child layers are visible by default:
                layers_to_set_not_visible.update(set(children))

                for ilayer in layers_to_set_not_visible:
                    self.state.layers[ilayer].visible = False

                # We can display the active data label in Compass plugin.
                self.set_compass(self.state.layers[next_layer].layer)

                # Update line profile plots too.
                if self.line_profile_xy is None:
                    try:
                        self.line_profile_xy = self.session.jdaviz_app.get_tray_item_from_name(
                            'imviz-line-profile-xy')
                    except KeyError:  # pragma: no cover
                        return
                self.line_profile_xy.viewer_selected = self.reference_id
                self.line_profile_xy.vue_draw_plot()

    def on_limits_change(self, *args):
        try:
            i = get_top_layer_index(self)
        except IndexError:
            if self.compass is not None:
                self.compass.clear_compass()
            return
        if i is None:
            return
        self.set_compass(self.state.layers[i].layer)

    @property
    def top_visible_data_label(self):
        """Data label of the top visible layer in the viewer."""
        try:
            i = get_top_layer_index(self)
        except IndexError:
            data_label = ''
        else:
            if i is None:
                data_label = ''
            else:
                data_label = self.state.layers[i].layer.label
        return data_label

    @property
    def first_loaded_data(self):
        """Data that is first loaded into the viewer.
        This may not be the visible layer.
        Returns `None` if no real data is loaded.
        """
        for lyr in self.layers:
            data = lyr.layer
            if layer_is_image_data(data):
                return data

    def _get_real_xy(self, image, x, y, reverse=False):
        """Return real (X, Y) position and status in case of dithering as well as whether the
        results were within the bounding box of the reference data or required possibly inaccurate
        extrapolation.

        ``coords_status`` is for ``CoordsInfo`` coords handling only.
        When `True`, it sets the coords, otherwise it resets.

        ``reverse=True`` is only for internal roundtripping (e.g., centroiding
        in Subset Tools plugin). Never use this for coordinates display panel.

        """
        # By default we'll assume the coordinates are valid and within any applicable bounding box.
        unreliable_world = False
        unreliable_pixel = False
        if data_has_valid_wcs(image):
            # Convert these to a SkyCoord via WCS - note that for other datasets
            # we aren't actually guaranteed to get a SkyCoord out, just for images
            # with valid celestial WCS
            try:
                link_type = self.get_link_type(image.label).lower()

                # Convert X,Y from reference data to the one we are actually seeing.
                # world_to_pixel return scalar ndarray that we need to convert to float.
                if link_type == 'wcs':
                    if not reverse:
                        outside_ref_bounding_box = wcs_utils.data_outside_gwcs_bounding_box(
                            self.state.reference_data, x, y)
                        x, y = list(map(float, pixel_to_pixel(
                            self.state.reference_data.coords, image.coords, x, y)))
                        outside_image_bounding_box = wcs_utils.data_outside_gwcs_bounding_box(
                            image, x, y)
                        unreliable_pixel = outside_image_bounding_box or outside_ref_bounding_box
                        unreliable_world = unreliable_pixel
                    else:
                        # We don't bother with unreliable_pixel and unreliable_world computation
                        # because this takes input (x, y) in the frame of visible layer and wants
                        # to convert it back to the frame of reference layer to pass back to the
                        # viewer. At this point, we no longer know if input (x, y) is accurate
                        # or not.
                        x, y = list(map(float, pixel_to_pixel(
                            image.coords, self.state.reference_data.coords, x, y)))
                else:  # pixels or self
                    unreliable_world = wcs_utils.data_outside_gwcs_bounding_box(image, x, y)

                coords_status = True
            except Exception:
                coords_status = False
        else:
            coords_status = False

        return x, y, coords_status, (unreliable_world, unreliable_pixel)

    def _get_zoom_limits(self, image):
        """Return a list of ``(x, y)`` that defines four corners of
        the zoom box for a given image.
        This is needed because viewer values are only based on reference
        image, which can be inaccurate if given image is dithered and
        they are linked by WCS.
        """
        if self.state.reference_data.meta.get('_WCS_ONLY', False):
            corner_world_coords = self.state.reference_data.coords.pixel_to_world(
                (self.state.x_min, self.state.x_min, self.state.x_max, self.state.x_max),
                (self.state.y_min, self.state.y_max, self.state.y_max, self.state.y_min)
            )
            # Convert X,Y from reference data to the one we are actually seeing.
            x = image.coords.world_to_pixel(corner_world_coords)
            zoom_limits = np.array(list(zip(x[0], x[1])))
        else:
            zoom_limits = np.array(((self.state.x_min, self.state.y_min),
                                    (self.state.x_min, self.state.y_max),
                                    (self.state.x_max, self.state.y_max),
                                    (self.state.x_max, self.state.y_min)))

        return zoom_limits

    def set_compass(self, image):
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
            norm=norm))

    def set_plot_axes(self):
        # self.figure.axes[1].tick_format = None
        # self.figure.axes[0].tick_format = None

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
            One of the link types accepted by the Orientation plugin
            or ``'self'`` if the data label belongs to the reference data itself.

        Raises
        ------
        ValueError
            Link look-up failed.

        """
        if len(self.session.application.data_collection) == 0:
            raise ValueError('No reference data for link look-up')

        ref_label = getattr(self.state.reference_data, 'label', None)
        if data_label == ref_label:
            return 'self'

        if ref_label in self.state.wcs_only_layers:
            return 'wcs'

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

    def _get_fov(self, wcs=None):
        if wcs is None:
            wcs = self.state.reference_data.coords
        if self.jdaviz_app._link_type != "wcs" or wcs is None:
            return

        # compute the mean of the height and width of the
        # viewer's FOV on ``data`` in world units:
        x_corners = [
            self.state.x_min,
            self.state.x_max,
            self.state.x_min
        ]
        y_corners = [
            self.state.y_min,
            self.state.y_min,
            self.state.y_max
        ]

        sky_corners = wcs.pixel_to_world(x_corners, y_corners)
        height_sky = abs(sky_corners[0].separation(sky_corners[2]))
        width_sky = abs(sky_corners[0].separation(sky_corners[1]))
        fov_sky = u.Quantity([height_sky, width_sky]).mean()
        return fov_sky

    def _get_center_skycoord(self, data=None):
        # get SkyCoord for the center of ``data`` in this viewer:
        x_cen = (self.state.x_min + self.state.x_max) * 0.5
        y_cen = (self.state.y_min + self.state.y_max) * 0.5

        if (self.jdaviz_app._link_type == "wcs" or data is None
                or data.label == self.state.reference_data.label):
            return self.state.reference_data.coords.pixel_to_world(x_cen, y_cen)

        if data.coords is not None:
            return data.coords.pixel_to_world(x_cen, y_cen)


class ScatterViewerState(GlueScatterViewerState):
    def _reset_att_limits(self, ax):
        # override glue's _reset_x/y_limits to account for all layers,
        # not just reference data
        att = f'{ax}_att'
        if getattr(self, att) is None:  # pragma: no cover
            return

        ax_min, ax_max = np.inf, -np.inf
        for layer in self.layers:
            ax_data = layer.layer.data.get_data(getattr(self, att))
            if len(ax_data) > 0:
                ax_min = min(ax_min, np.nanmin(ax_data))
                ax_max = max(ax_max, np.nanmax(ax_data))

        if not np.all(np.isfinite([ax_min, ax_max])):  # pragma: no cover
            return

        lim_helper = getattr(self, f'{ax}_lim_helper')
        lim_helper.lower = ax_min
        lim_helper.upper = ax_max
        lim_helper.update_values()

    def _reset_x_limits(self, *event):
        self._reset_att_limits('x')

    def _reset_y_limits(self, *event):
        self._reset_att_limits('y')

    def reset_limits(self, *event):
        x_min, x_max = np.inf, -np.inf
        y_min, y_max = np.inf, -np.inf

        for layer in self.layers:
            if not layer.visible:  # pragma: no cover
                continue

            x_data = layer.layer.data.get_data(self.x_att)
            y_data = layer.layer.data.get_data(self.y_att)

            x_min = min(x_min, np.nanmin(x_data))
            x_max = max(x_max, np.nanmax(x_data))
            y_min = min(y_min, np.nanmin(y_data))
            y_max = max(y_max, np.nanmax(y_data))

        x_lim_helper = getattr(self, 'x_lim_helper')
        x_lim_helper.lower = x_min
        x_lim_helper.upper = x_max

        y_lim_helper = getattr(self, 'y_lim_helper')
        y_lim_helper.lower = y_min
        y_lim_helper.upper = y_max

        x_lim_helper.update_values()
        y_lim_helper.update_values()

        self._adjust_limits_aspect()


@viewer_registry("imviz-scatter-viewer", label="scatter-viewer")
class ImvizScatterView(JdavizViewerMixin, BqplotScatterView):
    # categories: zoom resets, zoom, pan, subset, select tools, shortcuts
    tools_nested = [
                    ['jdaviz:homezoom', 'jdaviz:prevzoom'],
                    ['jdaviz:boxzoom', 'jdaviz:xrangezoom', 'jdaviz:yrangezoom'],
                    ['jdaviz:panzoom', 'jdaviz:panzoom_x', 'jdaviz:panzoom_y'],
                    ['bqplot:rectangle'],
                    ['bqplot:xrange', 'bqplot:yrange', 'bqplot:rectangle'],
                    ['jdaviz:sidebar_plot', 'jdaviz:sidebar_export']
                ]

    default_class = Table
    _state_cls = ScatterViewerState

    _native_mark_classnames = ('Image', 'ImageGL', 'Scatter', 'ScatterGL')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.display_mask = False
        self.time_unit = kwargs.get('time_unit', u.d)
        self.initialize_toolbar()
        self._subscribe_to_layers_update()
        # hack to inherit a small subset of methods from SpecvizProfileView
        # TODO: refactor jdaviz so these can be included in some mixin
        self._show_uncertainty_changed = lambda value: SpecvizProfileView._show_uncertainty_changed(self, value)  # noqa
        self._plot_uncertainties = lambda: SpecvizProfileView._plot_uncertainties(self)
        # TODO: _plot_uncertainties in specviz is hardcoded to look at spectral_axis and so crashes
        self._clean_error = lambda: SpecvizProfileView._clean_error(self)
        self.density_map = kwargs.get('density_map', False)

    def data(self, cls=None):
        data = []

        # TODO: generalize upstream in jdaviz.
        # This method is generalized from
        # jdaviz/configs/specviz/plugins/viewers.py
        # to support non-spectral viewers.
        for layer_state in self.state.layers:
            if hasattr(layer_state, 'layer'):
                lyr = layer_state.layer
                # For raw data, just include the data itself
                if isinstance(lyr, BaseData):
                    _class = cls or self.default_class

                    if _class is not None:
                        cache_key = lyr.label
                        if cache_key in self.jdaviz_app._get_object_cache:
                            layer_data = self.jdaviz_app._get_object_cache[cache_key]
                        else:
                            layer_data = lyr.get_object(cls=_class)
                            self.jdaviz_app._get_object_cache[cache_key] = layer_data

                        data.append(layer_data)

                # For subsets, make sure to apply the subset mask to the layer data first
                elif isinstance(lyr, (Subset, GroupedSubset)):
                    layer_data = lyr

                    if _class is not None:
                        handler, _ = data_translator.get_handler_for(_class)
                        try:
                            layer_data = handler.to_object(layer_data)
                        except IncompatibleAttribute:
                            continue
                    data.append(layer_data)

        return data

    def _apply_layer_defaults(self, layer_state):
        if getattr(layer_state.layer, 'meta', {}).get('Plugin', None) == 'Binning':
            # increased size of binned results, by default
            layer_state.size = 5

    def set_plot_axes(self):
        # set which components should be plotted
        dc = self.jdaviz_app.data_collection
        component_labels = [comp.label for comp in dc[0].components]

        # Get data to be used for axes labels
        data = self.data()[0]
        self._set_plot_x_axes(dc, component_labels, data)
        self._set_plot_y_axes(dc, component_labels, data)

    def _set_plot_x_axes(self, dc, component_labels, light_curve):
        self.state.x_att = component_ids['ra']

        self.figure.axes[0].label = "RA"
        self.figure.axes[0].num_ticks = 5

    def _set_plot_y_axes(self, dc, component_labels, light_curve):
        self.state.y_att = component_ids['dec']

        self.figure.axes[1].label = "Dec"

        # Make it so y axis label is not covering tick numbers (sometimes)
        self.figure.axes[1].label_offset = "-50"

        # Set (X,Y)-axis to scientific notation if necessary:
        self.figure.axes[0].tick_format = 'g'
        self.figure.axes[1].tick_format = 'g'

        self.figure.axes[1].num_ticks = 5

    def _expected_subset_layer_default(self, layer_state):
        super()._expected_subset_layer_default(layer_state)

        layer_state.linewidth = 3

        # optionally prevent subset from being rendered
        # as a density map, rather than shaded markers over data:
        layer_state.density_map = self.density_map

    def add_data(self, data, color=None, alpha=None, **layer_state):
        """
        Overrides the base class to handle subset styling defaults.

        Parameters
        ----------
        data : :class:`glue.core.data.Data`
            Data object with the light curve.
        color : obj
            Color value for plotting.
        alpha : float
            Alpha value for plotting.

        Returns
        -------
        result : bool
            `True` if successful, `False` otherwise.
        """
        result = super().add_data(data, color, alpha, **layer_state)

        for layer in self.layers:
            # optionally render as a density map
            layer.state.density_map = self.density_map

        # Set default linewidth on any created subset layers
        for layer in self.state.layers:
            if "Subset" in layer.layer.label and layer.layer.data.label == data.label:
                layer.linewidth = 3

        # update viewer limits when data are added
        self.set_plot_axes()
        self.state.reset_limits()

        return result

    def _show_uncertainty_changed(*args, **kwargs):
        # method required by jdaviz
        pass

    def apply_roi(self, roi, use_current=False):
        if isinstance(roi, RangeROI):
            # allow ROIs describing times to be applied with min and max defined as:
            #  1. floats, representing bounds in units of ``self.time_unit``
            #  2. Time objects, which get converted to work like (1) via the reference time
            if isinstance(roi.min, Time) or isinstance(roi.max, Time):
                reference_time = self.data()[0].meta.get('reference_time', 0)
                roi = roi.transformed(xfunc=lambda x: (x - reference_time).to_value(self.time_unit))

        super().apply_roi(roi, use_current=use_current)

    def on_limits_change(self):
        pass
