import numpy as np

from astropy.coordinates import SkyCoord
from astropy.table import QTable
from functools import cached_property
from glue.core import BaseData
from glue_jupyter.bqplot.image import BqplotImageView
from glue_jupyter.table import TableViewer
from scipy.interpolate import interp1d
from specutils import Spectrum1D

from jdaviz.core.events import (AddDataToViewerMessage,
                                RemoveDataFromViewerMessage,
                                TableClickMessage)
from jdaviz.core.astrowidgets_api import AstrowidgetsImageViewerMixin
from jdaviz.core.registries import viewer_registry
from jdaviz.core.freezable_state import FreezableBqplotImageViewerState
from jdaviz.configs.default.plugins.viewers import JdavizViewerMixin
from jdaviz.configs.specviz.plugins.viewers import SpecvizProfileView

__all__ = ['MosvizImageView', 'MosvizProfile2DView',
           'MosvizProfileView', 'MosvizTableViewer']


@viewer_registry("mosviz-image-viewer", label="Image 2D (Mosviz)")
class MosvizImageView(JdavizViewerMixin, BqplotImageView, AstrowidgetsImageViewerMixin):
    # categories: zoom resets, zoom, pan, subset, select tools, shortcuts
    tools_nested = [
                    ['jdaviz:homezoom', 'jdaviz:prevzoom'],
                    ['jdaviz:boxzoom'],
                    ['jdaviz:panzoom'],
                    ['jdaviz:sidebar_plot', 'jdaviz:sidebar_export']
                ]

    default_class = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_astrowidgets_api()
        self._subscribe_to_layers_update()

        self.state.show_axes = False  # Axes are wrong anyway
        self.figure.fig_margin = {'left': 0, 'bottom': 0, 'top': 0, 'right': 0}

    def data(self, cls=None):
        return [layer_state.layer.get_object(cls=cls or self.default_class)
                for layer_state in self.state.layers
                if hasattr(layer_state, 'layer') and
                isinstance(layer_state.layer, BaseData)]

    # NOTE: This is currently only for debugging. It is not used in app.
    def _mark_targets(self):
        table_data = self.jdaviz_app.data_collection['MOS Table']

        if ("R.A." not in table_data.component_ids() or
                "Dec." not in table_data.component_ids()):
            return

        ra = table_data["R.A."]
        dec = table_data["Dec."]
        sky = SkyCoord(ra, dec, unit='deg')
        t = QTable({'coord': sky})
        self.add_markers(t, use_skycoord=True, marker_name='Targets')


@viewer_registry("mosviz-profile-2d-viewer", label="Spectrum 2D (Mosviz)")
class MosvizProfile2DView(JdavizViewerMixin, BqplotImageView):
    # Due to limitations in CCDData and 2D data that has spectral and spatial
    #  axes, the default conversion class must handle cubes
    default_class = Spectrum1D

    # categories: zoom resets, zoom, pan, subset, select tools, shortcuts
    tools_nested = [
                    ['mosviz:homezoom'],
                    ['mosviz:boxzoom', 'mosviz:xrangezoom', 'jdaviz:yrangezoom'],
                    ['mosviz:panzoom', 'mosviz:panzoom_x', 'jdaviz:panzoom_y'],
                    ['bqplot:xrange'],
                    ['jdaviz:sidebar_plot', 'jdaviz:sidebar_export']
                ]

    _state_cls = FreezableBqplotImageViewerState

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._subscribe_to_layers_update()
        # Setup viewer option defaults
        self.state.aspect = 'auto'

        self._default_spectrum_viewer_reference_name = kwargs.get(
            "spectrum_viewer_reference_name", "spectrum-viewer"
        )
        self._default_spectrum_viewer_reference_name = kwargs.get(
            "spectrum_2d_viewer_reference_name", "spectrum-2d-viewer"
        )

        self.session.hub.subscribe(self, AddDataToViewerMessage,
                                   handler=self._on_viewer_data_changed)
        self.session.hub.subscribe(self, RemoveDataFromViewerMessage,
                                   handler=self._on_viewer_data_changed)

        for k in ('x_min', 'x_max'):
            self.state.add_callback(k, self._handle_x_axis_orientation)

    @cached_property
    def reference_spectral_axis(self):
        return self.state.reference_data.get_object().spectral_axis.value

    @cached_property
    def pixel_to_world_interp(self):
        pixels = range(len(self.reference_spectral_axis))
        return interp1d(pixels, self.reference_spectral_axis)

    def pixel_to_world_limits(self, limits):
        if not len(limits) == 2:
            raise ValueError("limits must be length 2")

        pixels = np.arange(0, len(self.reference_spectral_axis))

        # we'll use interpolation when possible, but also want to fit a line between
        # the outermost edge of the data within the limits
        line_edges_pix = np.array([max((min(pixels), min(limits))),
                                   min((max(pixels), max(limits)))])
        if line_edges_pix[0] > line_edges_pix[1]:
            # then the limits are entirely out of range, so use the whole range
            # when fitting the linear approximation
            line_edges_pix = np.array([min(pixels), max(pixels)])
        line_edges_world = self.pixel_to_world_interp(line_edges_pix)
        line_coeffs = np.polyfit(line_edges_pix, line_edges_world, deg=1)

        def pixel_to_world_line(pixel):
            return line_coeffs[0] * pixel + line_coeffs[1]

        def map_pixel_to_world(pixel):
            if pixels[0] <= pixel <= pixels[-1]:
                # interpolate directly
                return float(self.pixel_to_world_interp(pixel))
            else:
                # use the line model to extrapolate
                return pixel_to_world_line(pixel)

        invert = (-1) ** sum((self.inverted_x_axis, limits[0] > limits[1]))
        out_lims = list(map(map_pixel_to_world, limits))[::invert]

        return out_lims

    @cached_property
    def world_to_pixel_interp(self):
        pixels = range(len(self.reference_spectral_axis))
        return interp1d(self.reference_spectral_axis, pixels)

    def world_to_pixel_limits(self, limits):
        if not len(limits) == 2:
            raise ValueError("limits must be length 2")

        # we'll use interpolation when possible, but also want to fit a line between
        # the outermost edge of the data within the limits
        line_edges_world = np.array([max((min(self.reference_spectral_axis), min(limits))),
                                     min((max(self.reference_spectral_axis), max(limits)))])
        if line_edges_world[0] > line_edges_world[1]:
            # then the limits are entirely out of range, so use the whole range
            # when fitting the linear approximation
            line_edges_world = np.array([min(self.reference_spectral_axis),
                                         max(self.reference_spectral_axis)])
        line_edges_pixels = self.world_to_pixel_interp(line_edges_world)
        line_coeffs = np.polyfit(line_edges_world, line_edges_pixels, deg=1)

        def world_to_pixel_line(world):
            return line_coeffs[0] * world + line_coeffs[1]

        def map_world_to_pixel(world):
            if min(self.reference_spectral_axis) <= world <= max(self.reference_spectral_axis):
                # interpolate directly
                return float(self.world_to_pixel_interp(world))
            else:
                # use the line model to extrapolate
                return world_to_pixel_line(world)

        invert = (-1) ** sum((self.inverted_x_axis, limits[0] > limits[1]))
        out_lims = list(map(map_world_to_pixel, limits))[::invert]

        return out_lims

    def _on_viewer_data_changed(self, msg):
        if msg.viewer_reference != self.reference:
            return
        # clear cached properties that are based on reference data - this is probably
        # overly-conservative and we might be able to limit the clearing for only when
        # reference data is changed (perhaps with a callback on the state for reference_data)
        for attr in ('reference_spectral_axis', 'inverted_x_axis',
                     'pixel_to_world_interp', 'world_to_pixel_interp'):
            if attr in self.__dict__:
                del self.__dict__[attr]
        if len(self.data()):
            self._handle_x_axis_orientation()

    @cached_property
    def inverted_x_axis(self):
        return self.reference_spectral_axis[0] > self.reference_spectral_axis[-1]

    def _handle_x_axis_orientation(self, *args):
        x_scales = self.scales['x']
        limits = [x_scales.min, x_scales.max]
        limits_inverted = limits[0] > limits[1]
        if limits_inverted == self.inverted_x_axis:
            return
        with x_scales.hold_sync():
            x_scales.min = max(limits) if self.inverted_x_axis else min(limits)
            x_scales.max = min(limits) if self.inverted_x_axis else max(limits)

    def data(self, cls=None, statistic=None):
        return [layer_state.layer.get_object(statistic=statistic,
                                             cls=cls or self.default_class)
                for layer_state in self.state.layers
                if hasattr(layer_state, 'layer') and
                isinstance(layer_state.layer, BaseData)]

    def set_plot_axes(self):
        self.figure.axes[0].label = "x: pixels"

        self.figure.axes[1].label = "y: pixels"
        self.figure.axes[1].tick_format = None
        self.figure.axes[1].label_location = "start"

        # Make it so y axis label is not covering tick numbers.
        self.figure.axes[1].label_offset = "-50"


@viewer_registry("mosviz-profile-viewer", label="Profile 1D")
class MosvizProfileView(SpecvizProfileView):
    # categories: zoom resets, zoom, pan, subset, select tools, shortcuts
    tools_nested = [
                    ['mosviz:homezoom'],
                    ['mosviz:boxzoom', 'mosviz:xrangezoom', 'jdaviz:yrangezoom'],  # noqa
                    ['mosviz:panzoom', 'mosviz:panzoom_x', 'jdaviz:panzoom_y'],  # noqa
                    ['bqplot:xrange'],
                    ['jdaviz:selectline'],
                    ['jdaviz:sidebar_plot', 'jdaviz:sidebar_export']
                ]


@viewer_registry("mosviz-table-viewer", label="Table (Mosviz)")
class MosvizTableViewer(TableViewer, JdavizViewerMixin):
    def __init__(self, session, *args, **kwargs):
        super().__init__(session, *args, **kwargs)

        self.figure_widget.observe(self._on_row_selected, names=['highlighted'])
        # enable scrolling: # https://github.com/glue-viz/glue-jupyter/pull/287
        self.widget_table.scrollable = True

        self._selected_data = {}
        self._shared_image = False
        self.row_selection_in_progress = False

        self._on_row_selected_begin = None
        self._on_row_selected_end = None

        self._default_table_viewer_reference_name = kwargs.get(
            "table_viewer_reference_name", "table-viewer"
        )
        self._default_spectrum_viewer_reference_name = kwargs.get(
            "spectrum_viewer_reference_name", "spectrum-viewer"
        )
        self._default_spectrum_2d_viewer_reference_name = kwargs.get(
            "spectrum_2d_viewer_reference_name", "spectrum-2d-viewer"
        )
        self._default_image_viewer_reference_name = kwargs.get(
            "image_viewer_reference_name", "image-viewer"
        )

    def redraw(self):

        # Overload to hide components - we do this via overloading instead of
        # checking for changes in self.figure_widget.data because some components
        # might be added inplace to the dataset.

        if self.figure_widget.data is None:
            self.figure_widget.hidden_components = []
        else:
            components_str = [cid.label for cid in self.figure_widget.data.main_components]
            hidden = []
            for colname in ('Images', '1D Spectra', '2D Spectra'):
                if colname in components_str:
                    hidden.append(self.figure_widget.data.id[colname])
            self.figure_widget.hidden_components = hidden

        super().redraw()

    @property
    def nrows(self):
        return self.widget_table.get_state()['total_length']

    @property
    def current_row(self):
        return self.widget_table.highlighted

    def select_row(self, n):
        if n < 0 or n >= self.nrows:
            raise ValueError("n must be between 0 and {}".format(self.nrows-1))

        # compute and set the appropriate page
        # NOTE: traitlets won't detect internal changes to a dict
        options = self.widget_table.get_state()['options']
        page = int(n / options['itemsPerPage']) + 1
        if options['page'] != page:
            self.widget_table.set_state({'options': {**options, 'page': page}})
            self.widget_table.send_state()
        # select and highlight the row
        self.widget_table.highlighted = n

    def next_row(self):
        current_row = self.current_row
        new_row = 0 if current_row == self.nrows - 1 else current_row + 1
        self.select_row(new_row)

    def prev_row(self):
        current_row = self.current_row
        new_row = self.nrows - 1 if current_row == 0 else current_row - 1
        self.select_row(new_row)

    def _on_row_selected(self, event):
        if self._on_row_selected_begin:
            self._on_row_selected_begin(event)

        self.row_selection_in_progress = True
        # Grab the index of the latest selected row
        selected_index = event['new']
        mos_data = self.session.data_collection['MOS Table']

        # plugin data entries: select all in new row, deselect all others
        for data_item in self.jdaviz_app.data_collection:
            if data_item.meta.get('Plugin') is not None:
                if data_item.meta.get('mosviz_row') == selected_index:
                    self.session.hub.broadcast(AddDataToViewerMessage(
                        self._default_spectrum_viewer_reference_name, data_item.label, sender=self))
                else:
                    self.session.hub.broadcast(RemoveDataFromViewerMessage(
                        self._default_spectrum_viewer_reference_name, data_item.label, sender=self))

        for component in mos_data.components:
            comp_data = mos_data.get_component(component).data
            selected_data = comp_data[selected_index]

            if component.label == '1D Spectra':
                prev_data = self._selected_data.get(self._default_spectrum_viewer_reference_name)
                if prev_data != selected_data:
                    if prev_data:
                        # This covers the cases where data is unit converted
                        # and the name is modified
                        all_prev_data = [x
                                         for x in self.session.data_collection.labels
                                         if prev_data in x]
                        for modified_prev_data in all_prev_data:
                            if modified_prev_data:
                                remove_data_from_viewer_message = RemoveDataFromViewerMessage(
                                    self._default_spectrum_viewer_reference_name,
                                    modified_prev_data, sender=self
                                )
                                # reset the counter in the spectrum viewer's color cycler
                                # so that the newly selected row is displayed in gray and
                                # future additions will have other colors:
                                spectrum_viewer = self.jdaviz_app.get_viewer(
                                    self._default_spectrum_viewer_reference_name
                                )
                                spectrum_viewer.color_cycler.reset()

                                self.session.hub.broadcast(remove_data_from_viewer_message)

                    add_data_to_viewer_message = AddDataToViewerMessage(
                        self._default_spectrum_viewer_reference_name,
                        selected_data, sender=self
                    )
                    self.session.hub.broadcast(add_data_to_viewer_message)

                    self._selected_data[
                        self._default_spectrum_viewer_reference_name
                    ] = selected_data

            if component.label == '2D Spectra':
                prev_data = self._selected_data.get(self._default_spectrum_2d_viewer_reference_name)
                if prev_data != selected_data:
                    if prev_data:
                        remove_data_from_viewer_message = RemoveDataFromViewerMessage(
                            self._default_spectrum_2d_viewer_reference_name,
                            prev_data, sender=self
                        )
                        self.session.hub.broadcast(remove_data_from_viewer_message)

                    add_data_to_viewer_message = AddDataToViewerMessage(
                        self._default_spectrum_2d_viewer_reference_name,
                        selected_data, sender=self
                    )
                    self.session.hub.broadcast(add_data_to_viewer_message)

                    self._selected_data[
                        self._default_spectrum_2d_viewer_reference_name
                    ] = selected_data

            if component.label == 'Images':
                prev_data = self._selected_data.get(self._default_image_viewer_reference_name)
                if prev_data != selected_data:
                    if prev_data:
                        remove_data_from_viewer_message = RemoveDataFromViewerMessage(
                            self._default_image_viewer_reference_name, prev_data, sender=self)
                        self.session.hub.broadcast(remove_data_from_viewer_message)

                    add_data_to_viewer_message = AddDataToViewerMessage(
                        self._default_image_viewer_reference_name, selected_data, sender=self)
                    self.session.hub.broadcast(add_data_to_viewer_message)

                    self._selected_data[self._default_image_viewer_reference_name] = selected_data

        message = TableClickMessage(selected_index=selected_index,
                                    shared_image=self._shared_image,
                                    sender=self)
        self.session.hub.broadcast(message)

        self.row_selection_in_progress = False

        if self._on_row_selected_end:
            self._on_row_selected_end(event)

    def set_plot_axes(self, *args, **kwargs):
        return
