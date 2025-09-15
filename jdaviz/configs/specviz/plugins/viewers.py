import warnings

import numpy as np
from astropy import table
from matplotlib.colors import cnames
from specutils import Spectrum1D

from jdaviz.core.events import SpectralMarksChangedMessage, LineIdentifyMessage
from jdaviz.core.registries import viewer_registry
from jdaviz.core.marks import SpectralLine
from jdaviz.core.linelists import load_preset_linelist, get_available_linelists
from jdaviz.core.freezable_state import FreezableProfileViewerState
from jdaviz.configs.default.plugins.viewers import JdavizProfileView

__all__ = ['SpecvizProfileView']


@viewer_registry("specviz-profile-viewer", label="Profile 1D (Specviz)")
class SpecvizProfileView(JdavizProfileView):
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
    _default_profile_subset_type = 'spectral'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_menu._obj.dataset.add_filter('is_spectrum')

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
