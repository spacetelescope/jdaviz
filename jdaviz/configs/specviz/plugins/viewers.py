import warnings

import numpy as np
from astropy import table
from astropy import units as u
from functools import cached_property
from matplotlib.colors import cnames
from specutils import Spectrum
from scipy.interpolate import interp1d
from glue.core import BaseData
from glue_jupyter.bqplot.image import BqplotImageView

from jdaviz.core.events import (AddDataToViewerMessage,
                                RemoveDataFromViewerMessage,
                                SpectralMarksChangedMessage,
                                LineIdentifyMessage)
from jdaviz.core.freezable_state import FreezableBqplotImageViewerState
from jdaviz.core.registries import viewer_registry
from jdaviz.core.marks import SpectralLine
from jdaviz.core.linelists import load_preset_linelist, get_available_linelists
from jdaviz.core.unit_conversion_utils import (spectral_axis_conversion,
                                               flux_conversion_general,
                                               all_flux_unit_conversion_equivs)
from jdaviz.utils import SPECTRAL_AXIS_COMP_LABELS
from jdaviz.core.freezable_state import FreezableProfileViewerState
from jdaviz.configs.default.plugins.viewers import JdavizViewerMixin, JdavizProfileView

__all__ = ['Spectrum1DViewer', 'Spectrum2DViewer']


@viewer_registry("spectrum-1d-viewer", label="1D Spectrum")
class Spectrum1DViewer(JdavizProfileView):
    # categories: zoom resets, zoom, pan, subset, select tools, shortcuts
    tools_nested = [
                    ['jdaviz:homezoom_matchx', 'jdaviz:homezoom', 'jdaviz:prevzoom'],
                    ['jdaviz:boxzoom_matchx', 'jdaviz:xrangezoom_matchx', 'jdaviz:boxzoom', 'jdaviz:yrangezoom', 'jdaviz:xrangezoom', 'jdaviz:yrangezoom'],  # noqa
                    ['jdaviz:panzoom_matchx', 'jdaviz:panzoomx_matchx', 'jdaviz:panzoom_y', 'jdaviz:panzoom', 'jdaviz:panzoom_x', 'jdaviz:panzoom_y'],  # noqa
                    ['bqplot:xrange'],
                    ['jdaviz:selectline'],
                    ['jdaviz:viewer_clone', 'jdaviz:sidebar_plot', 'jdaviz:sidebar_export']
                ]

    default_class = Spectrum
    spectral_lines = None
    _state_cls = FreezableProfileViewerState
    _default_profile_subset_type = 'spectral'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        def compatible_units(data):
            if not len(self.layers):
                return True

            # If we load, e.g.,  one spectrum in Frequency and one in Wavelength,
            # the viewer state x_att won't match the component of the second spectrum since
            # (as of Specutils 2.X) they're no longer both the non-specific "World 0"
            if str(self.state.x_att) in data.component_ids():
                data_xunit = data.get_component(str(self.state.x_att)).units
            else:
                for comp in SPECTRAL_AXIS_COMP_LABELS:
                    if comp in data.component_ids():
                        data_xunit = data.get_component(comp).units
                        break
            data_yunit = data.get_component('flux').units

            viewer_xunit = self.state.x_display_unit
            viewer_yunit = self.state.y_display_unit

            if None in (data_xunit, data_yunit, viewer_xunit, viewer_yunit):
                return True

            try:
                spectral_axis_conversion([1], data_xunit, viewer_xunit)
            except u.UnitConversionError:
                return False
            equivs = all_flux_unit_conversion_equivs(cube_wave=[1]*u.Unit(viewer_xunit))
            try:
                flux_conversion_general([1], data_yunit, viewer_yunit, equivalencies=equivs)
            except u.UnitConversionError:
                return False

            return True

        self.data_menu._obj.dataset.add_filter('is_spectrum', compatible_units)
        self.data_menu.layer.add_filter('not_trace')

    @property
    def redshift(self):
        return self.jdaviz_helper._redshift

    def load_line_list(self, line_table, replace=False, return_table=False, show=True):
        # If string, load the named preset list and don't show by default
        # since there might be too many lines
        if isinstance(line_table, str):
            self.load_line_list(load_preset_linelist(line_table),
                                replace=replace, return_table=return_table,
                                show=False)
            return
        elif not isinstance(line_table, table.QTable):
            raise TypeError("Line list must be an astropy QTable with\
                            (minimally) 'linename' and 'rest' columns")
        if "linename" not in line_table.columns:
            raise ValueError("Line table must have a 'linename' column'")
        if "rest" not in line_table.columns:
            raise ValueError("Line table must have a 'rest' column'")
        if np.any(line_table['rest'] <= 0):
            raise ValueError("all rest values must be positive")

        # Use the redshift of the displayed spectrum if no redshifts are specified
        if "redshift" in line_table.colnames:
            warnings.warn("per line/list redshifts not supported, use viz.set_redshift")

        # Set whether to show all of the lines on the plot by default on load
        # We convert bool to int to work around ipywidgets json serialization
        line_table["show"] = int(show)

        # If there is already a loaded table, convert units to match. This
        # attempts to do some sane rounding after the unit conversion.
        # TODO: Fix this so that things don't get rounded to 0 in some cases
        """
        if self.spectral_lines is not None:
            sig_figs = []
            for row in line_table:
                rest_str = str(row["rest"].value).replace(".", "").split("e")[0]
                sig_figs.append(len(rest_str))
            line_table["rest"] = line_table["rest"].to(self.spectral_lines["rest"].unit)
            line_table["sig_figs"] = sig_figs
            for row in line_table:
                row["rest"] = row["rest"].round(row["sig_figs"])
            del line_table["sig_figs"]
        """

        # Combine name and rest value for indexing
        if "name_rest" not in line_table.colnames:
            line_table["name_rest"] = None
            for row in line_table:
                row["name_rest"] = "{} {}".format(row["linename"], row["rest"].value)

        # If no name was given to this list, consider it part of the "Custom" list
        if "listname" not in line_table.colnames:
            line_table["listname"] = "Custom"
        else:
            for row in line_table:
                if row["listname"] is None:
                    row["listname"] = "Custom"

        # Convert colors to hexa values, or set to default (red)
        if "colors" not in line_table.colnames:
            line_table["colors"] = "#FF0000FF"
        else:
            for row in line_table:
                if row["colors"][0] == "#":
                    if len(row["colors"]) == 6:
                        row["colors"] += "FF"
                else:
                    row["colors"] = cnames[row["colors"]] + "FF"

        # Create or update the main spectral_lines astropy table
        if self.spectral_lines is None or replace:
            self.spectral_lines = line_table
        else:
            self.spectral_lines = table.vstack([self.spectral_lines, line_table])
            self.spectral_lines = table.unique(self.spectral_lines, keys='name_rest')

        # It seems that we need to recreate this index after v-stacking.
        self.spectral_lines.add_index("name_rest")
        self.spectral_lines.add_index("linename")
        self.spectral_lines.add_index("listname")

        self._broadcast_plotted_lines()

        if return_table:
            return line_table

    def _broadcast_plotted_lines(self, marks=None):
        if marks is None:
            marks = [x for x in self.figure.marks if isinstance(x, SpectralLine)]

        msg = SpectralMarksChangedMessage(marks, sender=self)
        self.session.hub.broadcast(msg)

        if not np.any([mark.identify for mark in marks]):
            # then clear the identified entry
            msg = LineIdentifyMessage(name_rest='', sender=self)
            self.session.hub.broadcast(msg)

    def erase_spectral_lines(self, name=None, name_rest=None, show_none=True):
        """
        Erase either all spectral lines, all spectral lines sharing the same
        name (e.g. 'He II') or a specific name-rest value combination (e.g.
        'HE II 1640.5', stored in SpectralLine as 'table_index').
        """
        fig = self.figure
        if name is None and name_rest is None:
            fig.marks = [x for x in fig.marks if not isinstance(x, SpectralLine)]
            if show_none:
                self.spectral_lines["show"] = False
            self._broadcast_plotted_lines([])
        else:
            temp_marks = []
            # Toggle "show" value in main astropy table. The astropy table
            # machinery only allows updating a single row at a time.
            if name_rest is not None:
                if isinstance(name_rest, str):
                    self.spectral_lines.loc[name_rest]["show"] = False
                elif isinstance(name_rest, list):
                    for nr in name_rest:
                        self.spectral_lines.loc[nr]["show"] = False
            # Get rid of the marks we no longer want
            for x in fig.marks:
                if isinstance(x, SpectralLine):
                    if name is not None:
                        self.spectral_lines.loc[name]["show"] = False
                        if x.name == name:
                            continue
                    else:
                        if isinstance(name_rest, str):
                            if x.table_index == name_rest:
                                continue
                        elif isinstance(name_rest, list):
                            if x.table_index in name_rest:
                                continue
                temp_marks.append(x)
            fig.marks = temp_marks
            self._broadcast_plotted_lines()

    def plot_spectral_line(self, line, global_redshift=None, plot_units=None, **kwargs):
        if isinstance(line, str):
            # Try the full index first (for backend calls), otherwise name only
            try:
                line = self.spectral_lines.loc[line]
            except KeyError:
                line = self.spectral_lines.loc["linename", line]
        if plot_units is None:
            plot_units = self.data()[0].spectral_axis.unit

        if global_redshift is None:
            redshift = self.redshift
        else:
            redshift = global_redshift

        line_mark = SpectralLine(self,
                                 line['rest'].to_value(plot_units),
                                 redshift,
                                 name=line["linename"],
                                 table_index=line["name_rest"],
                                 colors=[line["colors"]], **kwargs)

        # Erase this line if it already existed, to avoid duplication
        self.erase_spectral_lines(name_rest=line["name_rest"])

        self.figure.marks = self.figure.marks + [line_mark]
        line["show"] = True
        self._broadcast_plotted_lines()

    def plot_spectral_lines(self, colors=["blue"], global_redshift=None, **kwargs):
        """
        Plots a user-provided astropy table of spectral lines in the viewer.
        """
        fig = self.figure
        self.erase_spectral_lines(show_none=False)

        # Check to see if colors were defined for each line
        if "colors" in self.spectral_lines.columns:
            colors = self.spectral_lines["colors"]
        elif len(colors) != len(self.spectral_lines):
            colors = colors*len(self.spectral_lines)

        lines = self.spectral_lines
        plot_units = self.data()[0].spectral_axis.unit

        if global_redshift is None:
            redshift = self.redshift
        else:
            redshift = global_redshift

        marks = []
        for line, color in zip(lines, colors):
            if not line["show"]:
                continue
            line = SpectralLine(self,
                                line['rest'].to_value(plot_units),
                                redshift,
                                name=line["linename"],
                                table_index=line["name_rest"],
                                colors=[color], **kwargs)
            marks.append(line)
        fig.marks = fig.marks + marks
        self._broadcast_plotted_lines()

    def available_linelists(self):
        return get_available_linelists()

    def set_plot_axes(self):
        super().set_plot_axes()
        self.figure.axes[1].num_ticks = 5


@viewer_registry('spectrum-2d-viewer', label="2D Spectrum")
class Spectrum2DViewer(JdavizViewerMixin, BqplotImageView):
    # Due to limitations in CCDData and 2D data that has spectral and spatial
    #  axes, the default conversion class must handle cubes
    default_class = Spectrum

    # categories: zoom resets, zoom, pan, subset, select tools, shortcuts
    tools_nested = [
                    ['jdaviz:homezoom_matchx', 'jdaviz:homezoom'],
                    ['jdaviz:boxzoom_matchx', 'jdaviz:xrangezoom_matchx',
                     'jdaviz:boxzoom', 'jdaviz:xrangezoom', 'jdaviz:yrangezoom'],
                    ['jdaviz:panzoom_matchx', 'jdaviz:panzoomx_matchx',
                     'jdaviz:panzoom', 'jdaviz:panzoom_x', 'jdaviz:panzoom_y'],
                    ['bqplot:xrange'],
                    ['jdaviz:viewer_clone', 'jdaviz:sidebar_plot', 'jdaviz:sidebar_export']
                ]

    _state_cls = FreezableBqplotImageViewerState

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._subscribe_to_layers_update()
        # Setup viewer option defaults
        self.state.aspect = 'auto'

        self.session.hub.subscribe(self, AddDataToViewerMessage,
                                   handler=self._on_viewer_data_changed)
        self.session.hub.subscribe(self, RemoveDataFromViewerMessage,
                                   handler=self._on_viewer_data_changed)

        for k in ('x_min', 'x_max'):
            self.state.add_callback(k, self._handle_x_axis_orientation)

        self.data_menu._obj.dataset.add_filter('is_2d_spectrum_or_trace')

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
        self.figure.axes[1].label_location = "middle"

        # Sync with Spectrum viewer (that is also used by other viz).
        # Make it so y axis label is not covering tick numbers.
        self.figure.fig_margin["left"] = 95
        self.figure.fig_margin["bottom"] = 60
        self.figure.send_state('fig_margin')  # Force update
        self.figure.axes[0].label_offset = "40"
        self.figure.axes[1].label_offset = "-70"
        # NOTE: with tick_style changed below, the default responsive ticks in bqplot result
        # in overlapping tick labels.  For now we'll hardcode at 8, but this could be removed
        # (default to None) if/when bqplot auto ticks react to styling options.
        self.figure.axes[1].num_ticks = 8

        for i in (0, 1):
            self.figure.axes[i].tick_style = {'font-size': 15, 'font-weight': 600}
