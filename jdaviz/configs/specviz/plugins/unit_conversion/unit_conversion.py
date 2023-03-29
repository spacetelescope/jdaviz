from astropy import units as u
from traitlets import Any, List, Unicode

from jdaviz.core.events import SnackbarMessage, AddDataMessage, RemoveDataMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin
from jdaviz.core.validunits import (create_spectral_equivalencies_list,
                                    create_flux_equivalencies_list)

__all__ = ['UnitConversion']


@tray_registry('g-unit-conversion', label="Unit Conversion",
               viewer_requirements='spectrum')
class UnitConversion(PluginTemplateMixin):

    template_file = __file__, "unit_conversion.vue"

    current_flux_unit = Unicode("").tag(sync=True)
    current_spectral_axis_unit = Unicode("").tag(sync=True)
    new_flux_unit = Any("").tag(sync=True)
    new_spectral_axis_unit = Any("").tag(sync=True)

    spectral_axis_unit_equivalencies = List([]).tag(sync=True)
    flux_unit_equivalencies = List([]).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._default_spectrum_viewer_reference_name = kwargs.get(
            "spectrum_viewer_reference_name", "spectrum-viewer"
        )
        self._viewer = self.app.get_viewer(self._default_spectrum_viewer_reference_name)

        self.session.hub.subscribe(self, AddDataMessage, handler=self._on_viewer_data_update)
        self.session.hub.subscribe(self, RemoveDataMessage, handler=self._on_viewer_data_update)

    def _on_viewer_data_update(self, msg):
        """Set UI label to show current flux and spectral axis units."""
        if self._viewer.state.y_display_unit:
            self.current_flux_unit = self._viewer.state.y_display_unit
        else:
            self.current_flux_unit = ""

        if self._viewer.state.x_display_unit:
            self.current_spectral_axis_unit = self._viewer.state.x_display_unit
        else:
            self.current_spectral_axis_unit = ""

        # Populate drop down with all valid options for unit conversion.
        x_u = u.Unit(self._viewer.state.x_display_unit)
        y_u = u.Unit(self._viewer.state.y_display_unit)
        self.flux_unit_equivalencies = create_flux_equivalencies_list(y_u, x_u)
        self.spectral_axis_unit_equivalencies = create_spectral_equivalencies_list(x_u)

    def vue_unit_conversion(self, *args, **kwargs):
        """
        Runs when the ``apply`` button is hit. Tries to change units if ``new`` units are set
        and are valid.
        """
        viewer = self._viewer
        update_axes = False
        error_msgs = []

        # TODO: DO we still have to worry about uncertainty and redshift?

        if self.new_flux_unit and (self.new_flux_unit != self.current_flux_unit):
            try:
                viewer.state.y_display_unit = self.new_flux_unit
            except Exception as e:
                error_msgs.append(repr(e))
            else:
                self.current_flux_unit = viewer.state.y_display_unit
                update_axes = True

        if (self.new_spectral_axis_unit and
                (self.new_spectral_axis_unit != self.current_spectral_axis_unit)):
            try:
                viewer.state.x_display_unit = self.new_spectral_axis_unit
            except Exception as e:
                error_msgs.append(repr(e))
            else:
                self.current_spectral_axis_unit = viewer.state.x_display_unit
                update_axes = True

        if update_axes:
            viewer.set_plot_axes()

        if error_msgs:
            self.hub.broadcast(SnackbarMessage(
                f"Unit conversion failed: {', '.join(error_msgs)}",
                color="error", sender=self))
