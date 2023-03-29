from astropy import units as u
from traitlets import List, Unicode, observe

from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, SelectPluginComponent, PluginUserApi
from jdaviz.core.validunits import (create_spectral_equivalencies_list,
                                    create_flux_equivalencies_list)

__all__ = ['UnitConversion']


@tray_registry('g-unit-conversion', label="Unit Conversion",
               viewer_requirements='spectrum')
class UnitConversion(PluginTemplateMixin):
    """
    The Unit Conversion plugin handles global app-wide unit-conversion.
    See the :ref:`Unit Conversion Plugin Documentation <unit-conversion>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * ``spectral_unit`` (:class:`~jdaviz.core.template_mixin.SelectPluginComponent`):
      Global unit to use for all spectral axes.
    * ``flux_unit`` (:class:`~jdaviz.core.template_mixin.SelectPluginComponent`):
      Global unit to use for all flux axes.
    """
    template_file = __file__, "unit_conversion.vue"

    spectral_unit_items = List().tag(sync=True)
    spectral_unit_selected = Unicode().tag(sync=True)
    flux_unit_items = List().tag(sync=True)
    flux_unit_selected = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO: support for multiple viewers
        # TODO: support for sky coordinate axes?
        # TODO: support for z-axes in image viewers
        # TODO: slice indicator broken after changing spectral_unit
        self.spectrum_viewer.state.add_callback('x_display_unit',
                                                self._on_glue_x_display_unit_changed)
        self.spectrum_viewer.state.add_callback('y_display_unit',
                                                self._on_glue_y_display_unit_changed)

        self.spectral_unit = SelectPluginComponent(self,
                                                   items='spectral_unit_items',
                                                   selected='spectral_unit_selected')
        self.flux_unit = SelectPluginComponent(self,
                                               items='flux_unit_items',
                                               selected='flux_unit_selected')

    @property
    def user_api(self):
        expose = []
        if self.config in ['specviz', 'specviz2d', 'cubeviz', 'mosviz']:
            expose += ['spectral_unit']
        expose += ['flux_unit']
        return PluginUserApi(self, expose=expose)

    def _on_glue_x_display_unit_changed(self, x_unit):
        if x_unit is None:
            return
        self.spectrum_viewer.set_plot_axes()
        if x_unit != self.spectral_unit.selected:
            x_u = u.Unit(x_unit)
            self.spectral_unit.choices = [x_unit] + create_spectral_equivalencies_list(x_u)
            self.spectral_unit.selected = x_unit
            if not len(self.flux_unit.choices):
                self._on_glue_y_display_unit_changed(self.spectrum_viewer.state.y_display_unit)

    def _on_glue_y_display_unit_changed(self, y_unit):
        if y_unit is None:
            return
        if self.spectral_unit.selected == "":
            # no spectral unit set yet, cannot determine equivalencies
            return
        self.spectrum_viewer.set_plot_axes()
        if y_unit != self.flux_unit.selected:
            x_u = u.Unit(self.spectral_unit.selected)
            y_u = u.Unit(y_unit)
            self.flux_unit.choices = [y_unit] + create_flux_equivalencies_list(y_u, x_u)
            self.flux_unit.selected = y_unit

    @observe('spectral_unit_selected')
    def _on_spectral_unit_changed(self, *args):
        if self.spectrum_viewer.state.x_display_unit != self.spectral_unit.selected:
            self.spectrum_viewer.state.x_display_unit = self.spectral_unit.selected

    @observe('flux_unit_selected')
    def _on_flux_unit_changed(self, *args):
        if self.spectrum_viewer.state.y_display_unit != self.flux_unit.selected:
            self.spectrum_viewer.state.y_display_unit = self.flux_unit.selected
