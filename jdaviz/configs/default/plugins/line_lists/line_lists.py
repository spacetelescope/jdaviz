import os
import pickle

import bqplot
from bqplot.marks import Lines
import astropy.units as u
from astropy.table import QTable
from glue.core.link_helpers import LinkSame
from glue.core.message import (SubsetCreateMessage,
                               SubsetDeleteMessage,
                               SubsetUpdateMessage)
from traitlets import Bool, Int, List, Unicode, Dict, Float

from jdaviz.core.events import (AddDataMessage,
                                RemoveDataMessage,
                                AddLineListMessage,
                                SnackbarMessage)
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.core.linelists import load_preset_linelist
from jdaviz.core.spectral_line import SpectralLine
from jdaviz.utils import load_template

__all__ = ['LineListTool']


@tray_registry('g-line-list', label="Line Lists")
class LineListTool(TemplateMixin):
    dialog = Bool(False).tag(sync=True)
    template = load_template("line_lists.vue", __file__).tag(sync=True)
    dc_items = List([]).tag(sync=True)
    available_lists = List([]).tag(sync=True)
    loaded_lists = List([]).tag(sync=True)
    list_contents = Dict({}).tag(sync=True)
    custom_name = Unicode().tag(sync=True)
    custom_rest = Unicode().tag(sync=True)
    custom_unit = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._viewer = self.app.get_viewer("spectrum-viewer")
        self._viewer_spectrum = None
        self._spectrum1d = None
        self.available_lists = self._viewer.available_linelists()
        self.list_to_load = None
        self.loaded_lists = ["Custom"]
        self.list_contents = {"Custom": {"lines": [], "color": "#FF0000FF"}}
        self.line_mark_dict = {}
        self._units = {}
        self._bounds = {}

        self.hub.subscribe(self, AddDataMessage,
                           handler=self._on_viewer_data_changed)

        self.hub.subscribe(self, RemoveDataMessage,
                           handler=self._on_viewer_data_changed)

        self.hub.subscribe(self, SubsetCreateMessage,
                           handler=lambda x: self._on_viewer_data_changed())

        self.hub.subscribe(self, SubsetDeleteMessage,
                           handler=lambda x: self._on_viewer_data_changed())

        self.hub.subscribe(self, SubsetUpdateMessage,
                           handler=lambda x: self._on_viewer_data_changed())

        self.hub.subscribe(self, AddLineListMessage,
                           handler=self._list_from_notebook)

    def _on_viewer_data_changed(self, msg=None):
        """
        Callback method for when data is added or removed from a viewer, or
        when a subset is created, deleted, or updated. This method receieves
        a glue message containing viewer information in the case of the former
        set of events, and updates the units in which to display the lines.

        Notes
        -----
        We do not attempt to parse any data at this point, at it can cause
        visible lag in the application.

        Parameters
        ----------
        msg : `glue.core.Message`
            The glue message passed to this callback method.
        """
        self._viewer_id = self.app._viewer_item_by_reference(
            'spectrum-viewer').get('id')

        # Subsets are global and are not linked to specific viewer instances,
        # so it's not required that we match any specific ids for that case.
        # However, if the msg is not none, check to make sure that it's the
        # viewer we care about.
        if msg is not None and msg.viewer_id != self._viewer_id:
            return

        try:
            viewer_data = self.app.get_viewer('spectrum-viewer').data()
        except TypeError:
            warn_message = SnackbarMessage("Line list plugin could not retrieve data from viewer",
                                            sender=self, color="error")
            self.hub.broadcast(warn_message)
            return

        # If no data is currently plotted, don't attempt to update
        if len(viewer_data) == 0:
            return

        self._viewer_spectrum = viewer_data[0]

        self._units["x"] = str(self._viewer_spectrum.spectral_axis.unit)
        self._units["y"] = str(self._viewer_spectrum.flux.unit)

        self._bounds["min"] = self._viewer_spectrum.spectral_axis[0]
        self._bounds["max"] = self._viewer_spectrum.spectral_axis[-1]

    def _list_from_notebook(self, msg):
        """
        Callback method for when a spectral line list is added to the specviz instance from the notebook.

        Parameters
        ----------
        msg : `glue.core.Message`
            The glue message passed to this callback method. Includes the line data added in msg.table.
        """
        list_contents = self.list_contents
        loaded_lists = self.loaded_lists
        for row in msg.table:
            if row["listname"] not in loaded_lists:
                loaded_lists.append(row["listname"])
            if row["listname"] not in list_contents:
                list_contents[row["listname"]] = {"lines": [], "color": "#FF0000FF"}
            temp_dict = {"linename": row["linename"],
                         "rest": row["rest"].value,
                         "unit": str(row["rest"].unit),
                         "colors": row["colors"] if "colors" in row else "#FF0000FF",
                         "show": True,
                         "name_rest": row["name_rest"]}
            list_contents[row["listname"]]["lines"].append(temp_dict)

        self.loaded_lists = []
        self.loaded_lists = loaded_lists
        self.list_contents = {}
        self.list_contents = list_contents

        lines_loaded_message = SnackbarMessage("Spectral lines loaded from notebook",
                                               sender=self, color="success")
        self.hub.broadcast(lines_loaded_message)

    def vue_update_available(self):
        """
        Check that the list to select from is up to date
        """
        self.available_lists = get_available_linelists()

    def update_line_mark_dict(self):
        self.line_mark_dict = {}
        for m in self._viewer.figure.marks:
            if type(m) == SpectralLine:
                self.line_mark_dict[m.table_index] = m

    def vue_list_selected(self, event):
        """
        Handle list selection from presets dropdown selector
        """
        self.list_to_load = event

    def vue_load_list(self, event):
        """
        Load one of the preset line lists, storing it's info in a
        vuetify-friendly manner in addition to loading the astropy table into
        the viewer's spectral_lines attribute.
        """
        # Don't need to reload an already loaded list
        if self.list_to_load in self.loaded_lists:
            return
        temp_table = load_preset_linelist(self.list_to_load)

        # Also store basic list contents in a form that vuetify can handle
        # Adds line style parameters that can be changed on the front end
        temp_table["colors"] = "#FF0000FF"

        # Load the table into the main astropy table and get it back, to make
        # sure all values match between the main table and local plugin
        temp_table = self._viewer.load_line_list(temp_table, return_table=True)

        line_list_dict = {"lines": [], "color": "#FF000080"}
        #extra_fields = [x for x in temp_table.colnames if x not in
        #                ("linename", "rest", "name_rest")]

        for row in temp_table:
            temp_dict = {"linename": row["linename"],
                         "rest": row["rest"].value,
                         "unit": str(row["rest"].unit),
                         "colors": row["colors"],
                         "show": True,
                         "name_rest": str(row["name_rest"])}
            #for field in extra_fields:
            #    temp_dict[field] = row[field]
            line_list_dict["lines"].append(temp_dict)

        list_contents = self.list_contents
        list_contents[self.list_to_load] = line_list_dict
        self.list_contents = {}
        self.list_contents = list_contents

        loaded_lists = self.loaded_lists + [self.list_to_load]
        self.loaded_lists = []
        self.loaded_lists = loaded_lists

        self._viewer.plot_spectral_lines()
        self.update_line_mark_dict()

        lines_loaded_message = SnackbarMessage("Spectral lines loaded from preset",
                                               sender=self, color="success")
        self.hub.broadcast(lines_loaded_message)

    def vue_add_custom_line(self, event):
        """
        Add a line to the "Custom" line list from UI input
        """
        list_contents = self.list_contents
        temp_dict = {"linename": self.custom_name,
                     "rest": float(self.custom_rest),
                     "unit": self.custom_unit,
                     "colors": list_contents["Custom"]["color"],
                     "show": True
                }

        # Add to viewer astropy table
        temp_table = QTable()
        temp_table["linename"] = [temp_dict["linename"]]
        temp_table["rest"] = [temp_dict["rest"]*u.Unit(temp_dict["unit"])]
        temp_table["colors"] = [temp_dict["colors"]]
        temp_table = self._viewer.load_line_list(temp_table, return_table=True)

        # Add line to Custom lines in local list
        temp_dict["name_rest"] = str(temp_table[0]["name_rest"])
        list_contents["Custom"]["lines"].append(temp_dict)
        self.list_contents = {}
        self.list_contents = list_contents

        self._viewer.plot_spectral_line(temp_dict["name_rest"])
        self.update_line_mark_dict()

        lines_loaded_message = SnackbarMessage("Custom spectral line loaded",
                                               sender=self, color="success")
        self.hub.broadcast(lines_loaded_message)

    def vue_show_all_in_list(self, listname):
        """
        Toggle all lines in list to be visible
        """
        lc = self.list_contents
        for line in lc[listname]["lines"]:
            line["show"] = True
            self._viewer.spectral_lines.loc[line["name_rest"]]["show"] = True
        # Trick traitlets into updating
        self.list_contents = {}
        self.list_contents = lc

        self._viewer.plot_spectral_lines()
        self.update_line_mark_dict()

    def vue_hide_all_in_list(self, listname):
        """
        Toggle all lines in list to be hidden
        """
        lc = self.list_contents
        name_rests = []
        for line in lc[listname]["lines"]:
            line["show"] = False
            name_rests.append(line["name_rest"])
        # Trick traitlets into updating
        self.list_contents = {}
        self.list_contents = lc

        self._viewer.erase_spectral_lines(name_rest=name_rests)
        self.update_line_mark_dict()

    def vue_plot_all_lines(self, event):
        """
        Plot all the currently loaded lines in the viewer
        """
        if self._viewer.spectral_lines is None:
            warn_message = SnackbarMessage("No spectral lines loaded to plot",
                                            sender=self, color="error")
            self.hub.broadcast(warn_message)
            return
        lc = self.list_contents
        for listname in lc:
            for line in lc[listname]["lines"]:
                line["show"] = True
        self._viewer.spectral_lines["show"] = True
        # Trick traitlets into updating
        self.list_contents = {}
        self.list_contents = lc

        self._viewer.plot_spectral_lines()
        self.update_line_mark_dict()

    def vue_erase_all_lines(self, event):
        """
        Erase all lines from the viewer
        """
        if self._viewer.spectral_lines is None:
            warn_message = SnackbarMessage("No spectral lines to erase",
                                            sender=self, color="error")
            self.hub.broadcast(warn_message)
            return
        lc = self.list_contents
        for listname in lc:
            for line in lc[listname]["lines"]:
                line["show"] = False
        # Trick traitlets into updating
        self.list_contents = {}
        self.list_contents = lc

        self._viewer.erase_spectral_lines()

    def vue_change_visible(self, line):
        """
        Plot or erase a single line as needed when "Visible" checkbox is changed
        """
        name_rest = line["name_rest"]
        if line["show"]:
            self._viewer.plot_spectral_line(name_rest)
            self.update_line_mark_dict()
        else:
            self._viewer.erase_spectral_lines(name_rest=name_rest)

    def vue_set_color(self, data):
        """
        Change the color either of all members of a line list, or of an
        individual line.
        """
        color = data['color']
        if "listname" in data:
            listname = data["listname"]
            lc = self.list_contents[listname]
            lc["color"] = color

            for line in lc["lines"]:
                line["colors"] = color
                # Update the astropy table entry
                name_rest = line["name_rest"]
                self._viewer.spectral_lines.loc[name_rest]["colors"] = color
                # Update the color on the plot
                if name_rest in self.line_mark_dict:
                    self.line_mark_dict[name_rest].colors = [color]

        elif "linename" in data:
            pass

    def vue_remove_list(self, listname):
        """
        Method to remove line list from available expansion panels when the x
        on the panel header is clicked. Also removes line marks from plot and
        updates the "show" value in the astropy table to False..
        """
        lc = self.list_contents[listname]
        name_rests = []
        for line in lc["lines"]:
            name_rests.append(self.vue_remove_line(line, erase=False))
        self._viewer.erase_spectral_lines(name_rest = name_rests)

        self.loaded_lists = [x for x in self.loaded_lists if x != listname]
        del(self.list_contents[listname])

    def vue_remove_line(self, line, erase=True):
        """
        Method to remove a line from the plot when the line is deselected in
        the expansion panel content. Input must have "linename" and "rest"
        values for indexing on the astropy table.
        """
        name_rest = line["name_rest"]
        # Keep in our spectral line astropy table, but set it to not show on plot
        self._viewer.spectral_lines.loc[name_rest]["show"] = False

        # Remove the line from the plot marks
        if erase:
            try:
                self._viewer.erase_spectral_lines(name_rest=name_rest)
                del(self.line_mark_dict[name_rest])
            except KeyError:
                raise KeyError("line marks: {}".format(self._viewer.figure.marks))
        else:
            return name_rest
