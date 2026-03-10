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
        Convenience function to load a line list and update the plugin UI.
        Delegates to the Line Lists plugin to avoid code duplication.
        """
        # Delegate to the Line Lists plugin's import method
        plg = self.app._jdaviz_helper.plugins['Line Lists']
        plg._obj.import_line_list(line_table)

    def _get_spectrum_viewer(self):
        """Get the spectrum viewer, handling both configured and deconfigged cases."""
        if hasattr(self, '_default_spectrum_viewer_reference_name'):
            return self.app.get_viewer(self._default_spectrum_viewer_reference_name)
        else:
            # For deconfigged, dynamically find the first spectrum viewer
            viewer_reference = self.app._get_first_viewer_reference_name(
                require_spectrum_viewer=True
            )
            if viewer_reference is None:
                return None
            return self.app.get_viewer(viewer_reference)

    def erase_spectral_lines(self, name=None):
        """Convenience function to get to the viewer function"""
        viewer = self._get_spectrum_viewer()
        if viewer is not None:
            viewer.erase_spectral_lines(name=name)

    def plot_spectral_line(self, line, global_redshift=None):
        """Convenience function to get to the viewer function"""
        viewer = self._get_spectrum_viewer()
        if viewer is not None:
            viewer.plot_spectral_line(line, global_redshift)

    def plot_spectral_lines(self, global_redshift=None):
        """Convenience function to get to the viewer function"""
        viewer = self._get_spectrum_viewer()
        if viewer is not None:
            viewer.plot_spectral_lines(global_redshift)

    @property
    def spectral_lines(self):
        viewer = self._get_spectrum_viewer()
        return viewer.spectral_lines if viewer is not None else None

    @property
    def available_linelists(self):
        viewer = self._get_spectrum_viewer()
        return viewer.available_linelists() if viewer is not None else []

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
