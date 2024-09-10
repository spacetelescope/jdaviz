from astropy import units as u
from glue.core.subset_group import GroupedSubset
from glue_jupyter.bqplot.image import BqplotImageView
import numpy as np
from traitlets import List, Unicode, observe, Bool

from jdaviz.configs.default.plugins.viewers import JdavizProfileView
from jdaviz.core.events import GlobalDisplayUnitChanged, AddDataMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin, UnitSelectPluginComponent,
                                        SelectPluginComponent, PluginUserApi)
from jdaviz.core.validunits import (create_spectral_equivalencies_list,
                                    create_flux_equivalencies_list,
                                    check_if_unit_is_per_solid_angle,
                                    create_angle_equivalencies_list)

__all__ = ['UnitConversion']


def _valid_glue_display_unit(unit_str, sv, axis='x'):
    # need to make sure the unit string is formatted according to the list of valid choices
    # that glue will accept (may not be the same as the defaults of the installed version of
    # astropy)
    if not unit_str:
        return unit_str
    unit_u = u.Unit(unit_str)
    choices_str = getattr(sv.state.__class__, f'{axis}_display_unit').get_choices(sv.state)
    choices_str = [choice for choice in choices_str if choice is not None]
    choices_u = [u.Unit(choice) for choice in choices_str]
    if unit_u not in choices_u:
        raise ValueError(f"{unit_str} could not find match in valid {axis} display units {choices_str}")  # noqa
    ind = choices_u.index(unit_u)
    return choices_str[ind]


def _flux_to_sb_unit(flux_unit, angle_unit):
    if angle_unit not in ['pix2', 'sr']:
        sb_unit = flux_unit
    elif '(' in flux_unit:
        pos = flux_unit.rfind(')')
        sb_unit = flux_unit[:pos] + ' ' + angle_unit + flux_unit[pos:]
    else:
        # append angle if there are no parentheses
        sb_unit = flux_unit + ' / ' + angle_unit

    return sb_unit


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
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.close_in_tray`
    * ``spectral_unit`` (:class:`~jdaviz.core.template_mixin.UnitSelectPluginComponent`):
      Global unit to use for all spectral axes.
    * ``flux_unit`` (:class:`~jdaviz.core.template_mixin.UnitSelectPluginComponent`):
      Global display unit for flux axis.
    * ``angle_unit`` (:class:`~jdaviz.core.template_mixin.UnitSelectPluginComponent`):
      Solid angle unit.
    * ``sb_unit`` (str): Read-only property for the current surface brightness unit,
      derived from the set values of ``flux_unit`` and ``angle_unit``.
    * ``spectral_y_type`` (:class:`~jdaviz.core.template_mixin.SelectPluginComponent`):
      Select the y-axis physical type for the spectrum-viewer (applicable only to Cubeviz).
    """
    template_file = __file__, "unit_conversion.vue"

    has_spectral = Bool(False).tag(sync=True)
    spectral_unit_items = List().tag(sync=True)
    spectral_unit_selected = Unicode().tag(sync=True)

    has_flux = Bool(False).tag(sync=True)
    flux_unit_items = List().tag(sync=True)
    flux_unit_selected = Unicode().tag(sync=True)

    has_angle = Bool(False).tag(sync=True)
    angle_unit_items = List().tag(sync=True)
    angle_unit_selected = Unicode().tag(sync=True)

    has_sb = Bool(False).tag(sync=True)
    sb_unit_selected = Unicode().tag(sync=True)

    has_time = Bool(False).tag(sync=True)
    time_unit_items = List().tag(sync=True)
    time_unit_selected = Unicode().tag(sync=True)

    spectral_y_type_items = List().tag(sync=True)
    spectral_y_type_selected = Unicode().tag(sync=True)

    # This shows an in-line warning message if False. This can be changed from
    # bool to unicode when we eventually handle inputing this value if it
    # doesn't exist in the FITS header
    pixar_sr_exists = Bool(True).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.config not in ['specviz', 'cubeviz']:
            # TODO [specviz2d, mosviz] x_display_unit is not implemented in glue for image viewer
            # used by spectrum-2d-viewer
            # TODO [mosviz]: add to yaml file
            # TODO [cubeviz, slice]: slice indicator broken after changing spectral_unit
            # TODO: support for multiple viewers and handling of mixed state from glue (or does
            # this force all to sync?)
            self.disabled_msg = f'This plugin is temporarily disabled in {self.config}. Effort to improve it is being tracked at GitHub Issue 1972.'  # noqa

        self.session.hub.subscribe(self, AddDataMessage,
                                   handler=self._on_add_data_to_viewer)

        self.has_spectral = self.config in ('specviz', 'cubeviz', 'specviz2d', 'mosviz')
        self.spectral_unit = UnitSelectPluginComponent(self,
                                                       items='spectral_unit_items',
                                                       selected='spectral_unit_selected')
        self.spectral_unit.choices = create_spectral_equivalencies_list(u.Hz)


        self.has_flux = self.config in ('specviz', 'cubeviz', 'specviz2d', 'mosviz')
        self.flux_unit = UnitSelectPluginComponent(self,
                                                   items='flux_unit_items',
                                                   selected='flux_unit_selected')
        # NOTE: will switch to count only if first data loaded into viewer in in counts
        self.flux_unit.choices = create_flux_equivalencies_list(u.Jy, u.Hz)

        self.has_angle = self.config in ('cubeviz', 'specviz', 'mosviz')
        self.angle_unit = UnitSelectPluginComponent(self,
                                                    items='angle_unit_items',
                                                    selected='angle_unit_selected')
        # NOTE: will switch to pix2 only if first data loaded into viewer is in pix2 units
        self.angle_unit.choices = create_angle_equivalencies_list(u.sr)

        self.has_sb = self.has_angle or self.config in ('imviz',)
        # NOTE: sb_unit is read_only, exposed through sb_unit property

        self.has_time = False
        self.time_unit = UnitSelectPluginComponent(self,
                                                   items='time_unit_items',
                                                   selected='time_unit_selected')

        self.spectral_y_type = SelectPluginComponent(self,
                                                     items='spectral_y_type_items',
                                                     selected='spectral_y_type_selected',
                                                     manual_options=['Surface Brightness', 'Flux'])

    @property
    def user_api(self):
        expose = []
        readonly = []
        if self.has_spectral:
            expose += ['spectral_unit']
        if self.has_flux:
            expose += ['flux_unit']
        if self.has_angle:
            expose += ['angle_unit']
        if self.has_sb:
            readonly = ['sb_unit']
        if self.has_time:
            expose += ['time_unit']
        if self.config == 'cubeviz':
            expose += ['spectral_y_type']
        return PluginUserApi(self, expose=expose, readonly=readonly)

    @property
    def sb_unit(self):
        # expose selected surface-brightness unit as read-only (rather than exposing a select object)
        return self.sb_unit_selected

    def _on_add_data_to_viewer(self, msg):
        # toggle warning message for cubes without PIXAR_SR defined
        if self.config == 'cubeviz':
            # NOTE: this assumes data_collection[0] is the science (flux/sb) cube
            if (
                len(self.app.data_collection) > 0
                and not self.app.data_collection[0].meta.get('PIXAR_SR')
            ):
                self.pixar_sr_exists = False

        viewer = msg.viewer

        # TODO: when enabling unit-conversion in rampviz, this may need to be more specific or handle other cases for ramp profile viewers
        if isinstance(viewer, JdavizProfileView):
            if viewer.state.x_display_unit == self.spectral_unit_selected and viewer.state.y_display_unit == self.app._get_display_unit('spectral_y'):
                # data already existed in this viewer and display units were already set
                return
            if not (len(self.spectral_unit_selected)
                    and len(self.flux_unit_selected)
                    and len(self.angle_unit_selected)
                    and (self.config != 'cubeviz' or len(self.spectral_y_type_selected))):

                spec = msg.data.get_object()

                self.spectral_unit._addl_unit_strings = self.spectrum_viewer.state.__class__.x_display_unit.get_choices(self.spectrum_viewer.state)
                if not len(self.spectral_unit_selected):
                    self.spectral_unit.selected = str(spec.spectral_axis.unit)

                angle_unit = check_if_unit_is_per_solid_angle(spec.flux.unit, return_unit=True)
                flux_unit = spec.flux.unit if angle_unit is None else spec.flux.unit * angle_unit

                if not self.flux_unit_selected:
                    if flux_unit in (u.count, u.DN):
                        self.flux_unit.choices = [flux_unit]
                    self.flux_unit.selected = str(flux_unit)

                if not self.angle_unit_selected:
                    if angle_unit == u.pix**2:
                        self.angle_unit.choices = ['pix2']

                    if angle_unit is None:
                        # default to sr if input spectrum is not in surface brightness units
                        # TODO: for cubeviz, should we check the cube itself?
                        self.angle_unit.selected = 'sr'
                    else:
                        self.angle_unit.selected = str(angle_unit)

                if not len(self.spectral_y_type_selected):
                    # set spectral_y_type_selected to 'Flux' if the y-axis unit is not per solid angle
                    if angle_unit is None:
                        self.spectral_y_type_selected = 'Flux'
                    else:
                        self.spectral_y_type_selected = 'Surface Brightness'

                # setting default values will trigger the observes to set the units in _on_unit_selected,
                # so return here to avoid setting twice
                return

            # this spectral viewer was empty (did not have display units set yet), but global selections
            # are available in the plugin, so we'll set them to the viewer here
            viewer.state.x_display_unit = self.spectral_unit_selected
            # _handle_spectral_y_unit will call viewer.set_plot_axes()
            self._handle_spectral_y_unit()

        elif isinstance(viewer, BqplotImageView):
            # set the attribute display unit (contour and stretch units) for the new layer
            # NOTE: this assumes that all image data is coerced to surface brightness units
            layers = [lyr for lyr in msg.viewer.layers if lyr.layer.data.label == msg.data.label]
            self._handle_attribute_display_unit(self.sb_unit_selected, layers=layers)


    @observe('spectral_unit_selected', 'flux_unit_selected',
             'angle_unit_selected', 'sb_unit_selected',
             'time_unit_selected')
    def _on_unit_selected(self, msg):
        """
        When any user selection is made, update the relevant viewer(s) with the new unit,
        and then emit a GlobalDisplayUnitChanged message to notify other plugins of the change.
        """
        if not len(msg.get('new', '')):
            # empty string, nothing to set yet
            return

        axis = msg.get('name').split('_')[0]

        if axis == 'spectral':
            xunit = _valid_glue_display_unit(self.spectral_unit.selected, self.spectrum_viewer, 'x')
            self.spectrum_viewer.state.x_display_unit = xunit
            self.spectrum_viewer.set_plot_axes()

        elif axis == 'flux':
            if len(self.angle_unit_selected):
                # NOTE: setting sb_unit_selected will call this method again with axis=='sb',
                # which in turn will call _handle_spectral_y_unit and send a second GlobalDisplayUnitChanged message for sb
                self.sb_unit_selected = _flux_to_sb_unit(self.flux_unit.selected, self.angle_unit.selected)

            if self.spectral_y_type_selected == 'Flux':
                self._handle_spectral_y_unit()

        elif axis == 'angle':
            if len(self.flux_unit_selected):
                # NOTE: setting sb_unit_selected will call this method again and send a second GlobalDisplayUnitChanged message for sb
                self.sb_unit_selected = _flux_to_sb_unit(self.flux_unit.selected, self.angle_unit.selected)

        elif axis == 'sb':
            self._handle_attribute_display_unit(self.sb_unit_selected)

            if self.spectral_y_type_selected == 'Surface Brightness':
                self._handle_spectral_y_unit()

        elif axis == 'time':
            pass

        # axis (first) argument will be one of: spectral, flux, angle, sb, time
        self.hub.broadcast(GlobalDisplayUnitChanged(msg.name.split('_')[0],
                           msg.new, sender=self))


    @observe('spectral_y_type_selected')
    def _handle_spectral_y_unit(self, *args):
        """
        When the spectral_y_type is changed, or the unit corresponding to the currently selected spectral_y_type is changed,
        update the y-axis of the spectrum viewer with the new unit, and then emit a GlobalDisplayUnitChanged message to notify
        """
        yunit_selected = self.sb_unit_selected if self.spectral_y_type_selected == 'Surface Brightness' else self.flux_unit_selected
        yunit = _valid_glue_display_unit(yunit_selected, self.spectrum_viewer, 'y')
        if self.spectrum_viewer.state.y_display_unit == yunit:
            return
        try:
            self.spectrum_viewer.state.y_display_unit = yunit
        except ValueError:
            # may not be data in the viewer, or unit may be incompatible
            pass
        else:
            self.spectrum_viewer.set_plot_axes()

            # broadcast that there has been a change in the spectrum viewer y axis,
            self.hub.broadcast(GlobalDisplayUnitChanged('spectral_y',
                                                        yunit,
                                                        sender=self))

 
    def _handle_attribute_display_unit(self, attr_unit, layers=None):
        """
        Update the per-layer attribute display unit in glue for image viewers (updating stretch and contour units).
        """
        if layers is None:
            layers = [layer
                      for viewer in self._app._viewer_store.values() if isinstance(viewer, BqplotImageView)
                      for layer in viewer.layers]
 
        for layer in layers:
            # DQ layer doesn't play nicely with this attribute
            if "DQ" in layer.layer.label or isinstance(layer.layer, GroupedSubset):
                continue
            elif u.Unit(layer.layer.get_component("flux").units).physical_type != 'surface brightness':  # noqa
                continue
            if hasattr(layer, 'attribute_display_unit'):
                layer.attribute_display_unit = attr_unit
