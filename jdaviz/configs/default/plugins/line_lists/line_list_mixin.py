from jdaviz.core.events import AddLineListMessage, RedshiftMessage

__all__ = ['LineListMixin']


class LineListMixin:
    """
    Line list-related methods and properties for use in the configuration
    helper classes.
    """

    _redshift = 0

    def load_line_list(self, line_table, replace=False):
        """
        Convenience function to get to the viewer function. Also
        broadcasts a message so the line list plugin UI can display lines
        loaded via the notebook.
        """

        lt = self.app.get_viewer(
            self._default_spectrum_viewer_reference_name
        ).load_line_list(
            line_table, replace=replace, return_table=True
        )

        # TODO: why is the rest of this logic here and not in viewer.load_line_list?

        # Preset lists were returning None table despite loading correctly
        if lt is None:
            if replace:
                lt = self.spectral_lines.loc["listname", line_table]
            else:
                lt = self.spectral_lines

        add_line_list_message = AddLineListMessage(table=lt, sender=self)
        self.app.hub.broadcast(add_line_list_message)

    def erase_spectral_lines(self, name=None):
        """Convenience function to get to the viewer function"""
        self.app.get_viewer(
            self._default_spectrum_viewer_reference_name
        ).erase_spectral_lines(name=name)

    def plot_spectral_line(self, line):
        """Convenience function to get to the viewer function"""
        self.app.get_viewer(
            self._default_spectrum_viewer_reference_name
        ).plot_spectral_line(line)

    def plot_spectral_lines(self):
        """Convenience function to get to the viewer function"""
        self.app.get_viewer(
            self._default_spectrum_viewer_reference_name
        ).plot_spectral_lines()

    @property
    def spectral_lines(self):
        return self.app.get_viewer(
            self._default_spectrum_viewer_reference_name
        ).spectral_lines

    @property
    def available_linelists(self):
        return self.app.get_viewer(
            self._default_spectrum_viewer_reference_name
        ).available_linelists()

    def set_redshift_slider_bounds(self, range=None, step=None):
        '''
        Set the range and/or step of the redshift slider. Set either/both to 'auto'
        for default values based on the limits of the spectrum plot.

        Parameters
        ----------
        range : float or `None` or 'auto'
            Specifies the difference between the upper and lower bounds of the slider.
            Note that the slider specifies delta redshift from the current value, so a
            range of 0.1 would allow the user to change the current redshift by +/- 0.05.
            If `None` or not passed, will leave at the current value. If 'auto',
            will sync the range based on the limits of the spectrum plot.
        step : float or `None` or 'auto'
            Specifies step size of the slider and redshift input (and will be converted to
            an estimated step for RV). Smaller step sizes will allow finer
            adjustments/smoother behavior at a potential cost to performance. If `None`
            or not passed, will leave at the current value. If 'auto', will sync
            the step size to 1000 steps within the current range.
        '''
        if range is not None:
            msg = RedshiftMessage("rs_slider_range", range, sender=self)
            self.app.hub.broadcast(msg)
        if step is not None:
            msg = RedshiftMessage("rs_slider_step", step, sender=self)
            self.app.hub.broadcast(msg)

    def set_redshift(self, new_redshift):
        '''
        Apply a redshift to any loaded spectral lines and data. Also updates
        the value shown in the slider.
        '''
        if new_redshift == self._redshift:
            # avoid sending messages that can result in race conditions
            return
        msg = RedshiftMessage("redshift", new_redshift, sender=self)
        self.app.hub.broadcast(msg)

    def _redshift_listener(self, msg):
        '''Save new redshifts (including from the helper itself)'''
        if msg.param == "redshift":
            self._redshift = msg.value
