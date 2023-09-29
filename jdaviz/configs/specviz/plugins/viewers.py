import warnings

import numpy as np
from astropy import table
from astropy import units as u
from astropy.nddata import StdDevUncertainty, VarianceUncertainty, InverseVariance
from echo import delay_callback
from glue.config import data_translator
from glue.core import BaseData
from glue.core.exceptions import IncompatibleAttribute
from glue.core.units import UnitConverter
from glue.core.subset import Subset
from glue.core.subset_group import GroupedSubset
from glue_astronomy.spectral_coordinates import SpectralCoordinates
from glue_jupyter.bqplot.profile import BqplotProfileView
from matplotlib.colors import cnames
from specutils import Spectrum1D

from jdaviz.core.events import SpectralMarksChangedMessage, LineIdentifyMessage, SnackbarMessage
from jdaviz.core.registries import viewer_registry
from jdaviz.core.marks import SpectralLine, LineUncertainties, ScatterMask, OffscreenLinesMarks
from jdaviz.core.linelists import load_preset_linelist, get_available_linelists
from jdaviz.core.freezable_state import FreezableProfileViewerState
from jdaviz.configs.default.plugins.viewers import JdavizViewerMixin
from jdaviz.utils import get_subset_type

__all__ = ['SpecvizProfileView']

uc = UnitConverter()

uncertainty_str_to_cls_mapping = {
    "std": StdDevUncertainty,
    "var": VarianceUncertainty,
    "ivar": InverseVariance
}


@viewer_registry("specviz-profile-viewer", label="Profile 1D (Specviz)")
class SpecvizProfileView(JdavizViewerMixin, BqplotProfileView):
    # categories: zoom resets, zoom, pan, subset, select tools, shortcuts
    tools_nested = [
                    ['jdaviz:homezoom', 'jdaviz:prevzoom'],
                    ['jdaviz:boxzoom', 'jdaviz:xrangezoom', 'jdaviz:yrangezoom'],
                    ['jdaviz:panzoom', 'jdaviz:panzoom_x', 'jdaviz:panzoom_y'],
                    ['bqplot:xrange'],
                    ['jdaviz:selectline'],
                    ['jdaviz:sidebar_plot', 'jdaviz:sidebar_export']
                ]

    default_class = Spectrum1D
    spectral_lines = None
    _state_cls = FreezableProfileViewerState

    def __init__(self, *args, **kwargs):
        default_tool_priority = kwargs.pop('default_tool_priority', [])
        super().__init__(*args, **kwargs)

        self._subscribe_to_layers_update()
        self.initialize_toolbar(default_tool_priority=default_tool_priority)
        self._offscreen_lines_marks = OffscreenLinesMarks(self)
        self.figure.marks = self.figure.marks + self._offscreen_lines_marks.marks

        self.state.add_callback('show_uncertainty', self._show_uncertainty_changed)

        self.display_mask = False

        # Change collapse function to sum
        self.state.function = 'sum'

    def _expected_subset_layer_default(self, layer_state):
        super()._expected_subset_layer_default(layer_state)

        layer_state.linewidth = 3

    def data(self, cls=None):
        # Grab the user's chosen statistic for collapsing data
        statistic = getattr(self.state, 'function', None)
        data = []

        for layer_state in self.state.layers:
            if hasattr(layer_state, 'layer'):
                lyr = layer_state.layer

                # For raw data, just include the data itself
                if isinstance(lyr, BaseData):
                    _class = cls or self.default_class

                    if _class is not None:
                        cache_key = (lyr.label, statistic)
                        if cache_key in self.jdaviz_app._get_object_cache:
                            layer_data = self.jdaviz_app._get_object_cache[cache_key]
                        else:
                            # If spectrum, collapse via the defined statistic
                            if _class == Spectrum1D:
                                layer_data = lyr.get_object(cls=_class, statistic=statistic)
                            else:
                                layer_data = lyr.get_object(cls=_class)
                            self.jdaviz_app._get_object_cache[cache_key] = layer_data

                        data.append(layer_data)

                # For subsets, make sure to apply the subset mask to the layer data first
                elif isinstance(lyr, Subset):
                    layer_data = lyr

                    if _class is not None:
                        handler, _ = data_translator.get_handler_for(_class)
                        try:
                            layer_data = handler.to_object(layer_data, statistic=statistic)
                        except IncompatibleAttribute:
                            continue
                    data.append(layer_data)

        return data

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

    def get_scales(self):
        fig = self.figure
        # Deselect any pan/zoom or subsetting tools so they don't interfere
        # with the scale retrieval
        if self.toolbar.active_tool is not None:
            self.toolbar.active_tool = None
        return {'x': fig.interaction.x_scale, 'y': fig.interaction.y_scale}

    def plot_spectral_line(self, line, plot_units=None, **kwargs):
        if isinstance(line, str):
            # Try the full index first (for backend calls), otherwise name only
            try:
                line = self.spectral_lines.loc[line]
            except KeyError:
                line = self.spectral_lines.loc["linename", line]
        if plot_units is None:
            plot_units = self.data()[0].spectral_axis.unit

        line_mark = SpectralLine(self,
                                 line['rest'].to(plot_units).value,
                                 self.redshift,
                                 name=line["linename"],
                                 table_index=line["name_rest"],
                                 colors=[line["colors"]], **kwargs)

        # Erase this line if it already existed, to avoid duplication
        self.erase_spectral_lines(name_rest=line["name_rest"])

        self.figure.marks = self.figure.marks + [line_mark]
        line["show"] = True
        self._broadcast_plotted_lines()

    def plot_spectral_lines(self, colors=["blue"], **kwargs):
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

        marks = []
        for line, color in zip(lines, colors):
            if not line["show"]:
                continue
            line = SpectralLine(self,
                                line['rest'].to(plot_units).value,
                                redshift=self.redshift,
                                name=line["linename"],
                                table_index=line["name_rest"],
                                colors=[color], **kwargs)
            marks.append(line)
        fig.marks = fig.marks + marks
        self._broadcast_plotted_lines()

    def available_linelists(self):
        return get_available_linelists()

    def _show_uncertainty_changed(self, msg=None):
        # this is subscribed in init to watch for changes to the state
        # object since uncertainty handling is in jdaviz instead of glue/glue-jupyter
        if self.state.show_uncertainty:
            self._plot_uncertainties()
        else:
            self._clean_error()

    def show_mask(self):
        self.display_mask = True
        self._plot_mask()

    def clean(self):
        # Remove extra traces, in case they exist.
        self.display_mask = False
        self._clean_mask()

        # this will automatically call _clean_error via _show_uncertainty_changed
        self.state.show_uncertainty = False

    def _clean_mask(self):
        fig = self.figure
        fig.marks = [x for x in fig.marks if not isinstance(x, ScatterMask)]

    def _clean_error(self):
        fig = self.figure
        fig.marks = [x for x in fig.marks if not isinstance(x, LineUncertainties)]

    def add_data(self, data, color=None, alpha=None, **layer_state):
        """
        Overrides the base class to add markers for plotting
        uncertainties and data quality flags.

        Parameters
        ----------
        spectrum : :class:`glue.core.data.Data`
            Data object with the spectrum.
        color : obj
            Color value for plotting.
        alpha : float
            Alpha value for plotting.

        Returns
        -------
        result : bool
            `True` if successful, `False` otherwise.
        """
        # If this is the first loaded data, set things up for unit conversion.
        if len(self.layers) == 0:
            reset_plot_axes = True
        else:
            # Check if the new data flux unit is actually compatible since flux not linked.
            try:
                uc.to_unit(data, data.find_component_id("flux"), [1, 1],
                           u.Unit(self.state.y_display_unit))  # Error if incompatible
            except Exception as err:
                # Raising exception here introduces a dirty state that messes up next load_data
                # but not raising exception also causes weird behavior unless we remove the data
                # completely.
                self.session.hub.broadcast(SnackbarMessage(
                    f"Failed to load {data.label}, so removed it: {repr(err)}",
                    sender=self, color='error'))
                self.jdaviz_app.data_collection.remove(data)
                return False
            reset_plot_axes = False

        # The base class handles the plotting of the main
        # trace representing the spectrum itself.
        result = super().add_data(data, color, alpha, **layer_state)

        if reset_plot_axes:
            x_units = data.get_component(self.state.x_att.label).units
            y_units = data.get_component("flux").units
            with delay_callback(self.state, "x_display_unit", "y_display_unit"):
                self.state.x_display_unit = x_units if len(x_units) else None
                self.state.y_display_unit = y_units if len(y_units) else None
            self.set_plot_axes()

        self._plot_uncertainties()

        self._plot_mask()

        # Set default linewidth on any created spectral subset layers
        # NOTE: this logic will need updating if we add support for multiple cubes as this assumes
        # that new data entries (from model fitting or gaussian smooth, etc) will only be spectra
        # and all subsets affected will be spectral
        for layer in self.state.layers:
            if (isinstance(layer.layer, GroupedSubset)
                    and get_subset_type(layer.layer) == 'spectral'
                    and layer.layer.data.label == data.label):
                layer.linewidth = 3

        return result

    def _plot_mask(self):
        if not self.display_mask:
            return

        # Remove existing mask marks
        self._clean_mask()

        # Loop through all active data in the viewer
        for index, layer_state in enumerate(self.state.layers):
            lyr = layer_state.layer
            comps = [str(component) for component in lyr.components]

            # Skip subsets
            if hasattr(lyr, "subset_state"):
                continue

            # Ignore data that does not have a mask component
            if "mask" in comps:
                mask = np.array(lyr['mask'].data)

                data_obj = lyr.data.get_object()
                data_x = data_obj.spectral_axis.value
                data_y = data_obj.flux.value

                # For plotting markers only for the masked data
                # points, erase un-masked data from trace.
                y = np.where(np.asarray(mask) == 0, np.nan, data_y)

                # A subclass of the bqplot Scatter object, ScatterMask places
                # 'X' marks where there is masked data in the viewer.
                color = layer_state.color
                alpha_shade = layer_state.alpha / 3
                mask_line_mark = ScatterMask(scales=self.scales,
                                             marker='cross',
                                             x=data_x,
                                             y=y,
                                             stroke_width=0.5,
                                             colors=[color],
                                             default_size=25,
                                             default_opacities=[alpha_shade]
                                             )
                # Add mask marks to viewer
                self.figure.marks = list(self.figure.marks) + [mask_line_mark]

    def _plot_uncertainties(self):
        if not self.state.show_uncertainty:
            return

        # Remove existing error bars
        self._clean_error()

        # Loop through all active data in the viewer
        for index, layer_state in enumerate(self.state.layers):
            lyr = layer_state.layer

            # Skip subsets
            if hasattr(lyr, "subset_state"):
                continue

            comps = [str(component) for component in lyr.components]

            # Ignore data that does not have an uncertainty component
            if "uncertainty" in comps:  # noqa
                error = np.array(lyr['uncertainty'].data)

                # ensure that the uncertainties are represented as stddev:
                uncertainty_type_str = lyr.meta.get('uncertainty_type', 'stddev')
                uncert_cls = uncertainty_str_to_cls_mapping[uncertainty_type_str]
                error = uncert_cls(error).represent_as(StdDevUncertainty).array

                # Then we assume that last axis is always wavelength.
                # This may need adjustment after the following
                # specutils PR is merged: https://github.com/astropy/specutils/pull/1033
                spectral_axis = -1
                data_obj = lyr.data.get_object(cls=Spectrum1D, statistic=None)

                if isinstance(lyr.data.coords, SpectralCoordinates):
                    spectral_wcs = lyr.data.coords
                    data_x = spectral_wcs.pixel_to_world_values(
                        np.arange(lyr.data.shape[spectral_axis])
                    )
                    if isinstance(data_x, tuple):
                        data_x = data_x[0]
                else:
                    if hasattr(lyr.data.coords, 'spectral_wcs'):
                        spectral_wcs = lyr.data.coords.spectral_wcs
                    elif hasattr(lyr.data.coords, 'spectral'):
                        spectral_wcs = lyr.data.coords.spectral
                    data_x = spectral_wcs.pixel_to_world(
                        np.arange(lyr.data.shape[spectral_axis])
                    )

                data_y = data_obj.data

                # The shaded band around the spectrum trace is bounded by
                # two lines, above and below the spectrum trace itself.
                data_x_list = np.ndarray.tolist(data_x)
                x = [data_x_list, data_x_list]
                y = [np.ndarray.tolist(data_y - error),
                     np.ndarray.tolist(data_y + error)]

                if layer_state.as_steps:
                    for i in (0, 1):
                        a = np.insert(x[i], 0, 2*x[i][0] - x[i][1])
                        b = np.append(x[i], 2*x[i][-1] - x[i][-2])
                        edges = (a + b) / 2
                        x[i] = np.concatenate((edges[:1], np.repeat(edges[1:-1], 2), edges[-1:]))
                        y[i] = np.repeat(y[i], 2)
                x, y = np.asarray(x), np.asarray(y)

                # A subclass of the bqplot Lines object, LineUncertainties keeps
                # track of uncertainties plotted in the viewer. LineUncertainties
                # appear with two lines and shaded area in between.
                color = layer_state.color
                alpha_shade = layer_state.alpha / 3
                error_line_mark = LineUncertainties(viewer=self,
                                                    x=[x],
                                                    y=[y],
                                                    scales=self.scales,
                                                    stroke_width=1,
                                                    colors=[color, color],
                                                    fill_colors=[color, color],
                                                    opacities=[0.0, 0.0],
                                                    fill_opacities=[alpha_shade,
                                                                    alpha_shade],
                                                    fill='between',
                                                    close_path=False
                                                    )

                # Add error lines to viewer
                self.figure.marks = list(self.figure.marks) + [error_line_mark]

    def set_plot_axes(self):
        # Set axes labels for the spectrum viewer
        flux_unit_type = "Flux density"
        x_disp_unit = self.state.x_display_unit
        x_unit = u.Unit(x_disp_unit) if x_disp_unit else u.dimensionless_unscaled
        if x_unit.is_equivalent(u.m):
            spectral_axis_unit_type = "Wavelength"
        elif x_unit.is_equivalent(u.Hz):
            spectral_axis_unit_type = "Frequency"
        elif x_unit.is_equivalent(u.pixel):
            spectral_axis_unit_type = "Pixel"
        else:
            spectral_axis_unit_type = str(x_unit.physical_type).title()

        with self.figure.hold_sync():
            self.figure.axes[0].label = f"{spectral_axis_unit_type} [{self.state.x_display_unit}]"
            self.figure.axes[1].label = f"{flux_unit_type} [{self.state.y_display_unit}]"

            # Make it so axis labels are not covering tick numbers.
            self.figure.fig_margin["left"] = 95
            self.figure.fig_margin["bottom"] = 60
            self.figure.send_state('fig_margin')  # Force update
            self.figure.axes[0].label_offset = "40"
            self.figure.axes[1].label_offset = "-70"
            # NOTE: with tick_style changed below, the default responsive ticks in bqplot result
            # in overlapping tick labels.  For now we'll hardcode at 8, but this could be removed
            # (default to None) if/when bqplot auto ticks react to styling options.
            self.figure.axes[1].num_ticks = 8

            # Set Y-axis to scientific notation
            self.figure.axes[1].tick_format = '0.1e'

            for i in (0, 1):
                self.figure.axes[i].tick_style = {'font-size': 15, 'font-weight': 600}
