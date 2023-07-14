import numpy as np
import os

import astropy.units as u
from astropy import constants as const
from astropy.table import QTable
from glue.core.message import (SubsetCreateMessage,
                               SubsetDeleteMessage,
                               SubsetUpdateMessage)
from glue_jupyter.common.toolbar_vuetify import read_icon
from traitlets import Any, Bool, Float, Int, List, Unicode, Dict, observe

from jdaviz.core.custom_traitlets import FloatHandleEmpty
from jdaviz.core.events import (AddDataMessage,
                                RemoveDataMessage,
                                AddLineListMessage,
                                LineIdentifyMessage,
                                SnackbarMessage,
                                RedshiftMessage,
                                SpectralMarksChangedMessage)
from jdaviz.core.linelists import load_preset_linelist, get_linelist_metadata
from jdaviz.core.marks import SpectralLine
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin
from jdaviz.core.tools import ICON_DIR
from jdaviz.core.validunits import create_spectral_equivalencies_list

__all__ = ['LineListTool']


@tray_registry(
    'g-line-list', label="Line Lists",
    viewer_requirements=['spectrum']
)
class LineListTool(PluginTemplateMixin):
    dialog = Bool(False).tag(sync=True)
    template_file = __file__, "line_lists.vue"

    rs_enabled = Bool(False).tag(sync=True)  # disabled until lines are plotted
    rs_slider = Float(0).tag(sync=True)  # in units of delta-redshift
    rs_slider_range_auto = Bool(True).tag(sync=True)
    rs_slider_half_range = Float(0.1).tag(sync=True)
    rs_slider_step_auto = Bool(True).tag(sync=True)
    rs_slider_step = Float(0.01).tag(sync=True)
    rs_slider_ndigits = Int(1).tag(sync=True)
    rs_slider_throttle = Int(100).tag(sync=True)
    rs_redshift = FloatHandleEmpty(0).tag(sync=True)
    rs_rv = FloatHandleEmpty(0).tag(sync=True)
    rs_rv_step = Float(1).tag(sync=True)

    dc_items = List([]).tag(sync=True)
    available_lists = List([]).tag(sync=True)
    loaded_lists = List([]).tag(sync=True)
    list_contents = Dict({}).tag(sync=True)
    custom_name = Unicode().tag(sync=True)
    custom_rest = Unicode().tag(sync=True)
    custom_unit_choices = List([]).tag(sync=True)
    custom_unit = Unicode().tag(sync=True)

    lines_filter = Any().tag(sync=True)  # string or None
    filter_range = Bool(False).tag(sync=True)
    spectrum_viewer_min = Float(0.01).tag(sync=True)
    spectrum_viewer_max = Float(0.01).tag(sync=True)

    identify_label = Unicode().tag(sync=True)
    identify_line_icon = Unicode(read_icon(os.path.join(ICON_DIR, 'line_select.svg'), 'svg+xml')).tag(sync=True)  # noqa
    filter_range_icon = Unicode(read_icon(os.path.join(ICON_DIR, 'spectral_range.svg'), 'svg+xml')).tag(sync=True)  # noqa

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._default_spectrum_viewer_reference_name = kwargs.get(
            "spectrum_viewer_reference_name", "spectrum-viewer"
        )
        self._default_flux_viewer_reference_name = kwargs.get(
            "flux_viewer_reference_name", "flux-viewer"
        )
        self._viewer = self.app.get_viewer(self._default_spectrum_viewer_reference_name)
        self._spectrum1d = None
        self.available_lists = self._viewer.available_linelists()
        self.list_to_load = None
        self.loaded_lists = ["Custom"]
        self.list_contents = {"Custom": {"lines": [],
                                         "color": "#FF0000FF",
                                         "medium": "Unknown (Custom)"}}
        self.line_mark_dict = {}
        self._units = {}
        self._bounds = {}
        self._global_redshift = 0
        self._rs_disable_observe = False
        self._rs_pause_tables = False
        # track which line was recently changed to avoid recursive updates due to imprecise
        # roundtripping
        self._rs_line_obs_change = (None, None)

        # Watch for messages from Specviz helper redshift functions
        self.hub.subscribe(self, RedshiftMessage,
                           handler=self._parse_redshift_msg)

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

        self.hub.subscribe(self, LineIdentifyMessage,
                           handler=self._process_identify_change)

        self.hub.subscribe(self, SpectralMarksChangedMessage,
                           handler=lambda x: self.update_line_mark_dict())

        # if set to auto (default), update the slider range when zooming on the spectrum viewer
        self._viewer.state.add_callback("x_min",
                                        lambda x_min: self._on_spectrum_viewer_limits_changed())
        self._viewer.state.add_callback("x_max",
                                        lambda x_max: self._on_spectrum_viewer_limits_changed())

        self._disable_if_no_data()

    def _disable_if_no_data(self):
        if len(self.app.data_collection) == 0:
            self.disabled_msg = 'Line Lists unavailable when no data is loaded'
        else:
            self.disabled_msg = ''

    def _on_viewer_data_changed(self, msg=None):
        """
        Callback method for when data is added or removed from a viewer, or
        when a subset is created, deleted, or updated. This method receives
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
        self._disable_if_no_data()

        self._viewer_id = self.app._viewer_item_by_reference(
            self._default_spectrum_viewer_reference_name).get('id')

        # Subsets are global and are not linked to specific viewer instances,
        # so it's not required that we match any specific ids for that case.
        # However, if the msg is not none, check to make sure that it's the
        # viewer we care about and that the message contains the data label.
        if msg is None or msg.viewer_id != self._viewer_id or msg.data is None:
            return

        label = msg.data.label
        try:
            viewer_data = self.app._jdaviz_helper.get_data(data_label=label)
        except TypeError:
            warn_message = SnackbarMessage("Line list plugin could not retrieve data from viewer",
                                           sender=self, color="error")
            self.hub.broadcast(warn_message)
            return

        # If no data is currently plotted, don't attempt to update
        if viewer_data is None:
            return

        if viewer_data.spectral_axis.unit == u.pix:
            # disable the plugin until we can address this properly (either using the wavelength
            # solution to support pixels in line-lists, or properly displaying the extracted
            # 1d spectrum in wavelength-space)
            self.disabled_msg = 'Line Lists unavailable when x-axis is in pixels'
        else:
            self.disabled_msg = ''

        self._units["x"] = str(viewer_data.spectral_axis.unit)
        self._units["y"] = str(viewer_data.flux.unit)

        self._bounds["min"] = viewer_data.spectral_axis[0]
        self._bounds["max"] = viewer_data.spectral_axis[-1]

        # set redshift slider to redshift stored in Spectrum1D object
        if viewer_data.meta.get('plugin', None) is not None:
            self.rs_redshift = (viewer_data.redshift.value
                                if hasattr(viewer_data.redshift, 'value')
                                else viewer_data.redshift)
        self._on_spectrum_viewer_limits_changed()  # will also trigger _auto_slider_step

        # set the choices (and default) for the units for new custom lines
        self.custom_unit_choices = create_spectral_equivalencies_list(
            viewer_data.spectral_axis.unit)
        self.custom_unit = str(viewer_data.spectral_axis.unit)

    def _parse_redshift_msg(self, msg):
        '''
        Handle incoming redshift messages from the app hub. Generally these
        will be created by Specviz helper methods.
        '''
        if msg.sender == self:
            return

        param = msg.param

        if param == "rs_slider_range":
            if msg.value == 'auto':
                # observer will handle setting rs_slider_range
                self.rs_slider_range_auto = True
            else:
                self.rs_slider_range_auto = False
                self.rs_slider_half_range = float(msg.value)/2
        elif param == "rs_slider_step":
            if msg.value == 'auto':
                # observer will handle setting rs_slider_step
                self.rs_slider_step_auto = True
            else:
                self.rs_slider_step_auto = False
                slider_step = float(msg.value)
                if slider_step > self.rs_slider_half_range:
                    raise ValueError("step must be smaller than range/2")
                self.rs_slider_step = slider_step
                self.rs_rv_step = self._redshift_to_velocity(slider_step)
        elif param == "redshift":
            # NOTE: this should trigger the observe to update rs_rv, line positions, and
            # update self._global_redshift
            self.rs_redshift = float(msg.value)
        elif param == 'rv':
            # NOTE: this should trigger the observe to update rs_redshift, line positions, and
            # update self._global_redshift
            self.rs_rv = float(msg.value)
        else:
            raise NotImplementedError(f"RedshiftMessage with param {param} not implemented.")

    def _velocity_to_redshift(self, velocity):
        """
        Convert a velocity to a relativistic redshift.  Assumes km/s (float)
        as input and returns float.
        """
        # NOTE: if supporting non-km/s units in the future, try to leave
        # the default case to avoid quantity math as below for efficiency
        beta = velocity * 1000 / const.c.value
        return np.sqrt((1 + beta) / (1 - beta)) - 1

    def _redshift_to_velocity(self, redshift):
        """
        Convert a relativistic redshift to a velocity.  Returns
        in km/s (float)
        """
        zponesq = (1 + redshift) ** 2
        # NOTE: if supporting non-km/s units in the future, try to leave
        # the default case to avoid quantity math as below for efficiency
        return const.c.value * (zponesq - 1) / (zponesq + 1) / 1000  # km/s

    def _update_line_positions(self):
        # update all lines, self._global_redshift, and emit message back to Specviz helper
        z = u.Quantity(self.rs_redshift)

        for mark in self.app.get_viewer(self._default_spectrum_viewer_reference_name).figure.marks:
            # update ALL to this redshift, if adding support for per-line redshift
            # this logic will need to change to not affect ALL lines
            if not isinstance(mark, SpectralLine):
                continue

            mark.redshift = z

    @observe('rs_slider')
    def _on_slider_updated(self, event):
        if self._rs_disable_observe:
            return

        self._rs_pause_tables = True

        # NOTE: _on_rs_redshift_updated will handle updating rs_rv
        # NOTE: the input has a custom @input method in line_lists.vue to cast
        # to float so that we can assume its a float here to minimize lag
        # when interacting with the slider.

        self.rs_redshift = np.round(self.rs_redshift + event['new'] - event['old'],
                                    self.rs_slider_ndigits)

    def _rest_to_obs(self, rest, redshift=None):
        if redshift is None:
            redshift = float(self.rs_redshift)

        return rest * (1+redshift)

    @observe('rs_redshift')
    def _on_rs_redshift_updated(self, event):
        if self._rs_disable_observe:
            return

        if not isinstance(event['new'], float):
            # then blank or None or '.'
            return

        value = event['new']
        # update _global_redshift so new lines, etc, will adopt this latest value
        self._global_redshift = value
        self._rs_disable_observe = True
        self.rs_rv = self._redshift_to_velocity(value)
        self._rs_disable_observe = False
        self._update_line_positions()

        if not self._rs_pause_tables:
            # TODO: try to avoid essentially repeating the loop from above, careful to minimize
            # updates to vue, maybe pause traitlets?
            self._update_line_list_obs()

            # Send the redshift back to the Specviz helper (and also trigger
            # self._update_global_redshift)
            msg = RedshiftMessage("redshift", value, sender=self)
            self.app.hub.broadcast(msg)

    def _update_line_list_obs(self, *args):
        for list_name, line_list in self.list_contents.items():
            for i, line in enumerate(line_list['lines']):
                if self._rs_line_obs_change[0] == list_name and self._rs_line_obs_change[1] == i:  # noqa
                    # this trigger is coming from a manual change to the observed
                    # wavelength and would result in a small change to the value before the
                    # user can finish typing.  So we'll just keep the old value until the
                    # widget is blurred (loses focus)
                    line_list['lines'][i]['obs'] = self._rs_line_obs_change[2]
                else:
                    line_list['lines'][i]['obs'] = self._rest_to_obs(float(line['rest']))

            self.list_contents[list_name] = line_list

        self.send_state('list_contents')

    def vue_change_line_obs(self, kwargs):
        # NOTE: we can only pass one argument from vue (it seems), so we'll pass as
        # a dictionary (kwargs) instead of positional or keyword arguments (**kwargs)
        line_obs = kwargs.get('obs_new')
        if isinstance(line_obs, str) and not len(line_obs):
            # empty string, we don't want to revert yet because then
            # the user can never delete the entry and type something new
            # so we'll just leave empty
            return
        list_name = kwargs.get('list_name')
        line_ind = kwargs.get('line_ind')
        line = self.list_contents[list_name]['lines'][line_ind]
        line_rest = float(line['rest'])
        if line_obs is None:
            # then coming from the blur, we'll keep the latest update from the @change
            line_obs = float(line['obs'])

        # we don't want this call to recursively update THIS obs wavelength, but DO want it to
        # update the RV and all other obs wavelengths.  Once tabbing or losing focus, vue will
        # send another event with avoid_feedback=False so that the wavelength updates to
        # exactly match the redshift (so that can be considered the ground truth value consistently)
        if kwargs.get('avoid_feedback', False):
            self._rs_line_obs_change = (list_name, line_ind, line_obs)
        # ensure tables will update when rs_redshift change is observed
        self._rs_pause_tables = kwargs.get('avoid_feedback', False)
        self.rs_redshift = (line_obs - line_rest) / line_rest
        self._rs_line_obs_change = (None, None)

    def vue_unpause_tables(self, event=None):
        # after losing focus, update any elements that were paused during changes
        self._rs_pause_tables = False
        self._rs_disable_observe = False
        self._on_rs_redshift_updated({'new': self.rs_redshift})

    @observe('rs_rv')
    def _on_rs_rv_updated(self, event):
        if self._rs_disable_observe:
            return

        if not isinstance(event['new'], float):
            # then blank or None or '.'
            return

        value = event['new']
        redshift = self._velocity_to_redshift(value)
        # prevent update the redshift from propagating back to an update in the rv
        self._rs_disable_observe = True
        # we'll wait until the blur event (which will call vue_unpause_tables)
        # to update the value in the MOS table and observed wavelengths
        self._rs_pause_tables = True
        self.rs_redshift = redshift
        # but we do want to update the plotted lines
        self._update_line_positions()

        self._rs_disable_observe = False

    def vue_slider_reset(self, event):
        self._rs_disable_observe = True
        self.rs_slider = 0.0
        self._rs_disable_observe = False
        self._rs_pause_tables = False
        # the redshift value in the MOS table and observed wavelengths weren't
        # updating during slide, so update them now
        self.vue_unpause_tables()

    def _on_spectrum_viewer_limits_changed(self, event=None):
        sv = self.app.get_viewer(self._default_spectrum_viewer_reference_name)
        if sv.state.x_min is None or sv.state.x_max is None:
            return
        self.spectrum_viewer_min = float(sv.state.x_min)
        self.spectrum_viewer_max = float(sv.state.x_max)

        # Also update the slider range
        self._auto_slider_range()

    def _auto_slider_range(self, event=None):
        """
        Automatically adjusts the Redshift slider range to the values of the
        spectrum_viewer_min and spectrum_viewer_max traitlets
        """
        if not self.rs_slider_range_auto:
            return
        # if set to auto, default the range based on the limits of the spectrum plot
        x_min, x_max = self.spectrum_viewer_min, self.spectrum_viewer_max
        x_mid = abs(x_max + x_min) / 2.
        # we'll *estimate* the redshift range to shift the range of the viewer
        # (for a line with a rest wavelength in the center of the viewer),
        # by taking abs, this will work for wavelength or frequency units.
        half_range = abs(x_max - x_min) / x_mid
        ndec = -np.log10(half_range)
        if ndec > 0 and not np.isinf(ndec):
            # round to at least 2 digits, or the first significant digit
            ndec = np.max([2, int(np.ceil(ndec))])
        else:
            ndec = 1
        half_range = np.round(half_range, ndec)

        # this will trigger self._auto_slider_step to set self.rs_slider_step and
        # self.rs_rv_step, if applicable
        self.rs_slider_half_range = half_range

    @observe('rs_slider_range_auto')
    def _on_rs_slider_range_auto_updated(self, event):
        if event['new']:
            self._on_spectrum_viewer_limits_changed()

    @observe('rs_slider_half_range')
    def _auto_slider_step(self, event=None):
        if not self.rs_slider_step_auto:
            return
        # if set to auto, default to 1000 steps in the range
        self.rs_slider_step = self.rs_slider_half_range * 2 / 1000
        self.rs_rv_step = abs(self._redshift_to_velocity(self._global_redshift+self.rs_slider_step) - self.rs_rv) # noqa

    @observe('rs_slider_step')
    def _on_rs_slider_step_updated(self, event):
        # When using the slider, we'll "round" redshift to the digits in the
        # slider step to avoid extra digits due to rounding errors
        ndec = -np.log10(event['new'])
        if ndec > 0 and not np.isinf(ndec):
            # round to at least 2 digits, or one past the first significant digit
            # note: the UI will not show trailing zeros, we just want to avoid
            # and 1 at floating point precision if not significant
            ndec = np.max([2, np.ceil(ndec)+1])
        else:
            ndec = 1
        self.rs_slider_ndigits = int(ndec)

    @observe('rs_slider_step_auto')
    def _on_rs_slider_step_auto_updated(self, event):
        if event['new']:
            self._auto_slider_step()

    def _update_global_redshift(self, msg):
        '''Handle updates to the Specviz redshift slider, to apply to lines'''
        if msg.param == "redshift":
            self._global_redshift = msg.value

    def _list_from_notebook(self, msg):
        """
        Callback method for when a spectral line list is added to the specviz
        instance from the notebook.

        Parameters
        ----------
        msg : `glue.core.Message`
            The glue message passed to this callback method. Includes the line
            data added in msg.table.
        """
        loaded_lists = self.loaded_lists
        list_contents = self.list_contents
        tmp_names_rest = []
        for row in msg.table:
            if row["listname"] not in loaded_lists:
                loaded_lists.append(row["listname"])

            if row["listname"] not in list_contents:
                list_contents[row["listname"]] = {"lines": [], "color": "#FF0000FF"}

            temp_dict = {"linename": row["linename"],
                         "rest": row["rest"].value,
                         "obs": self._rest_to_obs(row["rest"].value),
                         "unit": str(row["rest"].unit),
                         "colors": row["colors"] if "colors" in row else "#FF0000FF",
                         "show": row["show"],
                         "name_rest": row["name_rest"]}
            list_contents[row["listname"]]["lines"].append(temp_dict)
            tmp_names_rest.append(row["name_rest"])

        self.send_state('loaded_lists')
        self.send_state('list_contents')

        self._viewer.plot_spectral_lines(tmp_names_rest)
        self.update_line_mark_dict()

        msg_text = ("Spectral lines loaded from notebook. Lines can be hidden"
                    "/shown in the Line Lists plugin")
        lines_loaded_message = SnackbarMessage(msg_text, sender=self,
                                               color="success", timeout=15000)
        self.hub.broadcast(lines_loaded_message)

    def update_line_mark_dict(self):
        self.line_mark_dict = {}
        for m in self._viewer.figure.marks:
            if isinstance(m, SpectralLine):
                self.line_mark_dict[m.table_index] = m

        n_lines_shown = len(self.line_mark_dict)

        # redshift controls are enabled if any lines are currently plotted
        self.rs_enabled = n_lines_shown > 0

        if n_lines_shown > 0:
            # with a lot of lines, a quick slider move will lag.  Let's scale the
            # timeout based on the number of lines, roughtly between 50-500 ms
            throttle = n_lines_shown * 5
            if throttle < 50:
                throttle = 50
            if throttle > 500:
                throttle = 500
            self.rs_slider_throttle = throttle

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
        temp_table = self._viewer.load_line_list(temp_table, return_table=True,
                                                 show=False)

        metadata = get_linelist_metadata()
        list_medium = metadata[self.list_to_load].get('medium', 'Unknown').capitalize()

        line_list_dict = {"lines": [], "color": "#FF000080", "medium": list_medium}
        # extra_fields = [x for x in temp_table.colnames if x not in
        #                ("linename", "rest", "name_rest")]

        for row in temp_table:
            temp_dict = {"linename": row["linename"],
                         "rest": row["rest"].value,
                         "obs": self._rest_to_obs(row["rest"].value),
                         "unit": str(row["rest"].unit),
                         "colors": row["colors"],
                         "show": False,
                         "name_rest": str(row["name_rest"])}
            # for field in extra_fields:
            #     temp_dict[field] = row[field]
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

        msg_text = ("Spectral lines loaded from preset. Lines can be shown/hidden"
                    f" in the {self.list_to_load} dropdown in the Line Lists plugin")
        lines_loaded_message = SnackbarMessage(msg_text, sender=self,
                                               color="success", timeout=15000)
        self.hub.broadcast(lines_loaded_message)

    def vue_add_custom_line(self, event):
        """
        Add a line to the "Custom" line list from UI input
        """
        list_contents = self.list_contents
        temp_dict = {"linename": self.custom_name,
                     "rest": float(self.custom_rest),
                     "obs": self._rest_to_obs(float(self.custom_rest)),
                     "unit": self.custom_unit,
                     "colors": list_contents["Custom"]["color"],
                     "show": True
                     }

        # Add to viewer astropy table

        with u.set_enabled_equivalencies(u.spectral()):
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

        self.list_contents = lc
        self.send_state('list_contents')

        self._viewer.plot_spectral_lines()
        self.update_line_mark_dict()

    def vue_hide_all_in_list(self, listname):
        """
        Toggle all lines in list to be hidden
        """
        name_rests = []
        for line in self.list_contents[listname]["lines"]:
            line["show"] = False
            name_rests.append(line["name_rest"])

        self.send_state('list_contents')

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
        for listname in self.list_contents:
            for line in self.list_contents[listname]["lines"]:
                line["show"] = True
        self._viewer.spectral_lines["show"] = True

        self.send_state('list_contents')

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
        for listname in self.list_contents:
            for line in self.list_contents[listname]["lines"]:
                line["show"] = False

        self.send_state('list_contents')

        self._viewer.erase_spectral_lines()
        self.update_line_mark_dict()

    def vue_change_visible(self, data):
        """
        Plot or erase a single line as needed when "Visible" checkbox is changed
        """
        listname, line, line_ind = data
        name_rest = line["name_rest"]
        show = not line['show']

        list_contents = self.list_contents
        list_contents[listname]['lines'][line_ind]['show'] = show
        if not show:
            # then make sure to also disable the identify flag
            list_contents[listname]['lines'][line_ind]['identify'] = False
        self.list_contents = {}
        self.list_contents = list_contents

        if show:
            self._viewer.plot_spectral_line(name_rest)
        else:
            self._viewer.erase_spectral_lines(name_rest=name_rest)

        self.update_line_mark_dict()

    def _update_identify_to_line(self, name_rest, listname=None, identify=True):
        list_contents = self.list_contents
        for this_listname, this_list in list_contents.items():
            for i, line in enumerate(this_list['lines']):
                if ((this_listname == listname or listname is None) and
                        line['name_rest'] == name_rest):
                    list_contents[this_listname]['lines'][i]['identify'] = identify
                else:
                    list_contents[this_listname]['lines'][i]['identify'] = False

        self.list_contents = {}
        self.list_contents = list_contents
        self.identify_label = name_rest if identify else ""

    def _process_identify_change(self, msg):
        if msg.sender == self:
            return
        # event from some other plugin (LineAnalysis, for example) requesting a change
        # in the identified line
        self._update_identify_to_line(msg.name_rest)
        # then line mark themselves will also respond to the same event, so there is
        # no need to broadcast another

    def vue_set_identify(self, data=None):
        """
        Set the selected line as "identified"
        """
        if data is None:
            # then default to the currently identified (which will unidentify it)
            for listname, this_list in self.list_contents.items():
                for line_ind, line in enumerate(this_list['lines']):
                    if line['identify']:
                        return self.vue_set_identify((listname, line, line_ind))

        listname, line, line_ind = data
        identify = not line.get('identify', False)
        if identify and not line['show']:
            # first show the line
            self.vue_change_visible(data)

        self._update_identify_to_line(name_rest=line['name_rest'],
                                      listname=listname,
                                      identify=identify)

        # broadcast and event to update the marks
        msg = LineIdentifyMessage(name_rest=line['name_rest'] if identify else '',
                                  sender=self)
        self.hub.broadcast(msg)

    def vue_set_color(self, data):
        """
        Change the color either of all members of a line list, or of an
        individual line.
        """
        color = data['color']
        if "listname" in data:
            listname = data["listname"]

            self.list_contents[listname]["color"] = color

            for line in self.list_contents[listname]["lines"]:
                line["colors"] = color
                # Update the astropy table entry
                name_rest = line["name_rest"]
                self._viewer.spectral_lines.loc[name_rest]["colors"] = color
                # Update the color on the plot
                if name_rest in self.line_mark_dict:
                    self.line_mark_dict[name_rest].colors = [color]

            self.send_state('list_contents')

        elif "linename" in data:
            pass

    def vue_remove_list(self, listname):
        """
        Method to remove line list from available expansion panels when the x
        on the panel header is clicked. Also removes line marks from plot and
        updates the "show" value in the astropy table to False.
        """
        lc = self.list_contents[listname]
        name_rests = []
        for line in lc["lines"]:
            name_rests.append(self.vue_remove_line(line, erase=False))
        self._viewer.erase_spectral_lines(name_rest=name_rests)
        self.update_line_mark_dict()

        self.loaded_lists = [x for x in self.loaded_lists if x != listname]
        self.list_contents = {k: v for k, v in self.list_contents.items() if k != listname}
        row_inds = [i for i, ln in
                    enumerate(self._viewer.spectral_lines['listname'])
                    if ln != listname]
        if len(row_inds) == 0:
            self._viewer.spectral_lines = None
        else:
            self._viewer.spectral_lines = self._viewer.spectral_lines[row_inds]

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
                del self.line_mark_dict[name_rest]
            except KeyError:
                raise KeyError("line marks: {}".format(self._viewer.figure.marks))
        else:
            return name_rest
