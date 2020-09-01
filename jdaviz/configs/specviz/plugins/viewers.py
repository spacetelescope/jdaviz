from glue.core import BaseData
from glue_jupyter.bqplot.profile import BqplotProfileView
from astropy import table
from specutils import Spectrum1D
from matplotlib.colors import cnames

from jdaviz.core.registries import viewer_registry
from jdaviz.core.spectral_line import SpectralLine
from jdaviz.core.linelists import load_preset_linelist, get_available_linelists

__all__ = ['SpecvizProfileView']


@viewer_registry("specviz-profile-viewer", label="Profile 1D (Specviz)")
class SpecvizProfileView(BqplotProfileView):
    default_class = Spectrum1D
    spectral_lines = None

    def data(self, cls=None):
        return [layer_state.layer.get_object(cls=cls or self.default_class)
                for layer_state in self.state.layers
                if hasattr(layer_state, 'layer') and
                isinstance(layer_state.layer, BaseData)]

    def load_line_list(self, line_table, replace=False, return_table=False):
        if type(line_table) == str:
            self.load_line_list(load_preset_linelist(line_table),
                                replace=replace, raise_event=raise_event)
            return
        elif type(line_table) != table.QTable:
            raise TypeError("Line list must be an astropy QTable with\
                            (minimally) 'linename' and 'rest' columns")
        if "linename" not in line_table.columns:
            raise ValueError("Line table must have a 'linename' column'")
        if "rest" not in line_table.columns:
            raise ValueError("Line table must have a 'rest' column'")

        # Use the redshift of the displayed spectrum if no redshifts are specified
        if "redshift" not in line_table.colnames:
            line_table["redshift"] = self.data()[0].spectral_axis.redshift

        # Set all of the lines to be shown on the plot by default on load
        line_table["show"] = True

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

        if return_table:
            return line_table

    def erase_spectral_lines(self, name=None, name_rest=None, show_none=True):
        """
        Erase either all spectral lines, all spectral lines sharing the same
        name (e.g. 'He II') or a specific name-rest value combination (e.g.
        'HE II 1640.5', stored in SpectralLine as 'table_index').
        """
        fig = self.figure
        if name is None and name_rest is None:
            fig.marks = [x for x in fig.marks if type(x) != SpectralLine]
            if show_none:
                self.spectral_lines["show"] = False
        else:
            temp_marks = []
            # Toggle "show" value in main astropy table
            if name_rest is not None:
                self.spectral_lines.loc[name_rest]["show"] = False
            # Get rid of the marks we no longer want
            for x in fig.marks:
                if type(x) == SpectralLine:
                    if name is not None:
                        self.spectral_lines.loc[name]["show"] = False
                        if x.name == name:
                            continue
                    else:
                        self.spectral_lines.loc[name_rest]["show"] = False
                        if type(name_rest) == str:
                            if x.table_index == name_rest:
                                continue
                        elif type(name_rest) == list:
                            if x.table_index in name_rest:
                                continue
                temp_marks.append(x)
            fig.marks = temp_marks

    def get_scales(self):
        fig = self.figure
        # Deselect any pan/zoom or subsetting tools so they don't interfere
        # with the scale retrieval
        if self.toolbar.active_tool is not None:
            self.toolbar.active_tool = None
        return {'x': fig.interaction.x_scale, 'y':fig.interaction.y_scale}

    def plot_spectral_line(self, line, scales=None, plot_units=None, **kwargs):
        if type(line) == str:
            line = self.spectral_lines.loc[line]
        if plot_units is None:
            plot_units = self.data()[0].spectral_axis.unit
        if scales is None:
            scales = self.get_scales()
        # Calculate observed wavelength based on redshift
        line_val = line["rest"].to(plot_units).value * (1+line['redshift'])

        line_mark = SpectralLine(line_val, scales, name=line["linename"],
                                 table_index=line["name_rest"],
                                 colors=[line["colors"]], **kwargs)

        # Erase this line if it already existed, to avoid duplication
        self.erase_spectral_lines(name_rest=line["name_rest"])

        self.figure.marks = self.figure.marks + [line_mark]
        line["show"] = True

    def plot_spectral_lines(self, colors=["blue"], **kwargs):
        """
        Plots a user-provided astropy table of spectral lines in the viewer.
        """
        fig = self.figure
        self.erase_spectral_lines(show_none=False)

        scales = self.get_scales()

        # Check to see if colors were defined for each line
        if "colors" in self.spectral_lines.columns:
            colors = self.spectral_lines["colors"]
        elif len(colors) != len(self.spectral_lines):
            colors = colors*len(self.spectral_lines)

        # Retrieve redshift from table or plotted spectrum
        if "redshift" in self.spectral_lines.columns:
            redshifts = self.spectral_lines["redshift"]
        else:
            redshifts = [self.data()[0].redshift]*len(self.spectral_lines)

        lines = self.spectral_lines
        plot_units = self.data()[0].spectral_axis.unit

        for i in range(len(lines)):
            if not lines[i]["show"]:
                continue
            line_val = lines[i]["rest"].to(plot_units).value * (1+redshifts[i])
            line = SpectralLine(line_val, scales, name=lines[i]["linename"],
                                table_index=lines[i]["name_rest"],
                                colors=[colors[i]], **kwargs)
            fig.marks = fig.marks + [line]

    def available_linelists(self):
        return get_available_linelists()
