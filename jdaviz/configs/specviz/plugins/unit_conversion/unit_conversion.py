from contextlib import nullcontext
from functools import cached_property

from astropy import units as u
from glue.core.subset_group import GroupedSubset
from glue_jupyter.bqplot.image import BqplotImageView
from specutils import Spectrum1D
from traitlets import List, Unicode, observe, Bool

from jdaviz.configs.default.plugins.viewers import JdavizProfileView
from jdaviz.core.custom_units_and_equivs import _eqv_flux_to_sb_pixel, _eqv_pixar_sr
from jdaviz.core.events import GlobalDisplayUnitChanged, AddDataMessage, SliceValueUpdatedMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin, UnitSelectPluginComponent,
                                        SelectPluginComponent, PluginUserApi)
from jdaviz.core.unit_conversion_utils import (create_equivalent_spectral_axis_units_list,
                                               create_equivalent_flux_units_list,
                                               check_if_unit_is_per_solid_angle,
                                               create_equivalent_angle_units_list,
                                               supported_sq_angle_units)

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
    if angle_unit not in supported_sq_angle_units(as_strings=True):
        sb_unit = flux_unit
    else:
        # str > unit > str to remove formatting inconsistencies with
        # parentheses/order of units/etc
        sb_unit = (u.Unit(flux_unit) / u.Unit(angle_unit)).to_string()

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
    * ``spectral_y_unit``: Read-only property for the current y-axis unit in the spectrum-viewer,
      either ``flux_unit`` or ``sb_unit`` depending on the selected ``spectral_y_type``
      (applicable only to Cubeviz).
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

        # description displayed under plugin title in tray
        self._plugin_description = 'Convert the units of displayed physical quantities.'

        self._cached_properties = ['image_layers']

        if self.config not in ['specviz', 'specviz2d', 'cubeviz']:
            # TODO [mosviz] x_display_unit is not implemented in glue for image viewer
            # TODO [mosviz]: add to yaml file
            # TODO [cubeviz, slice]: slice indicator broken after changing spectral_unit
            # TODO: support for multiple viewers and handling of mixed state from glue (or does
            # this force all to sync?)
            self.disabled_msg = f'This plugin is temporarily disabled in {self.config}. Effort to improve it is being tracked at GitHub Issue 1972.'  # noqa

        self.session.hub.subscribe(self, AddDataMessage,
                                   handler=self._on_add_data_to_viewer)
        self.session.hub.subscribe(self, SliceValueUpdatedMessage,
                                   handler=self._on_slice_changed)

        self.has_spectral = self.config in ('specviz', 'cubeviz', 'specviz2d', 'mosviz')
        self.spectral_unit = UnitSelectPluginComponent(self,
                                                       items='spectral_unit_items',
                                                       selected='spectral_unit_selected')
        self.spectral_unit.choices = create_equivalent_spectral_axis_units_list(u.Hz)

        self.has_flux = self.config in ('specviz', 'cubeviz', 'specviz2d', 'mosviz')
        self.flux_unit = UnitSelectPluginComponent(self,
                                                   items='flux_unit_items',
                                                   selected='flux_unit_selected')
        # NOTE: will switch to count only if first data loaded into viewer in in counts
        # initialize flux choices to empty list, will be populated when data is loaded
        self.flux_unit.choices = []

        self.has_angle = self.config in ('cubeviz', 'specviz', 'mosviz', 'specviz2d')
        self.angle_unit = UnitSelectPluginComponent(self,
                                                    items='angle_unit_items',
                                                    selected='angle_unit_selected')
        # NOTE: will switch to pix2 only if first data loaded into viewer is in pix2 units
        # initialize angle unit choices to empty list, will be populated when data is loaded
        self.angle_unit.choices = []

        self.has_sb = self.has_angle or self.config in ('imviz',)
        # NOTE: sb_unit is read_only, exposed through sb_unit property

        self.has_time = False
        self.time_unit = UnitSelectPluginComponent(self,
                                                   items='time_unit_items',
                                                   selected='time_unit_selected')

        self.spectral_y_type = SelectPluginComponent(self,
                                                     items='spectral_y_type_items',
                                                     selected='spectral_y_type_selected')

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
            expose += ['spectral_y_type', 'spectral_y_unit']
        return PluginUserApi(self, expose=expose, readonly=readonly)

    @property
    def sb_unit(self):
        # expose selected surface-brightness unit as read-only
        # (rather than exposing a select object)
        return self.sb_unit_selected

    @property
    def spectral_y_unit(self):
        return self.sb_unit_selected if self.spectral_y_type_selected == 'Surface Brightness' else self.flux_unit_selected  # noqa

    @cached_property
    def image_layers(self):
        return [layer
                for viewer in self._app._viewer_store.values() if isinstance(viewer, BqplotImageView)  # noqa
                for layer in viewer.layers]

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

        if (not len(self.spectral_unit_selected)
                or not len(self.flux_unit_selected)
                or not len(self.angle_unit_selected)
                or (self.config == 'cubeviz' and not len(self.spectral_y_type_selected))):
            data_obj = msg.data.get_object()
            if isinstance(data_obj, Spectrum1D):

                self.spectral_unit._addl_unit_strings = self.spectrum_viewer.state.__class__.x_display_unit.get_choices(self.spectrum_viewer.state)  # noqa
                if not len(self.spectral_unit_selected):
                    try:
                        self.spectral_unit.selected = str(data_obj.spectral_axis.unit)
                    except ValueError:
                        self.spectral_unit.selected = ''

                angle_unit = check_if_unit_is_per_solid_angle(data_obj.flux.unit, return_unit=True)
                flux_unit = data_obj.flux.unit if angle_unit is None else data_obj.flux.unit * angle_unit  # noqa

                if not self.flux_unit_selected:
                    self.flux_unit.choices = create_equivalent_flux_units_list(flux_unit)
                    try:
                        self.flux_unit.selected = str(flux_unit)
                    except ValueError:
                        self.flux_unit.selected = ''

                if not self.angle_unit_selected:
                    self.angle_unit.choices = create_equivalent_angle_units_list(angle_unit)

                    try:
                        if angle_unit is None:
                            if self.config in ['specviz', 'specviz2d']:
                                self.has_angle = False
                                self.has_sb = False
                            else:
                                # default to pix2 if input data is not in surface brightness units
                                # TODO: for cubeviz, should we check the cube itself?
                                self.angle_unit.selected = 'pix2'
                        else:
                            self.angle_unit.selected = str(angle_unit)
                    except ValueError:
                        self.angle_unit.selected = ''

                if (not len(self.spectral_y_type_selected)
                        and isinstance(viewer, JdavizProfileView)):
                    # set spectral_y_type_selected to 'Flux'
                    # if the y-axis unit is not per solid angle
                    self.spectral_y_type.choices = ['Surface Brightness', 'Flux']
                    if angle_unit is None:
                        self.spectral_y_type_selected = 'Flux'
                    else:
                        self.spectral_y_type_selected = 'Surface Brightness'

                # setting default values will trigger the observes to set the units
                # in _on_unit_selected, so return here to avoid setting twice
                return

        # TODO: when enabling unit-conversion in rampviz, this may need to be more specific
        # or handle other cases for ramp profile viewers
        if isinstance(viewer, JdavizProfileView):
            if (viewer.state.x_display_unit == self.spectral_unit_selected
                    and viewer.state.y_display_unit == self.spectral_y_unit):
                # data already existed in this viewer and display units were already set
                return

            # this spectral viewer was empty (did not have display units set yet),˜
            # but global selections are available in the plugin,
            # so we'll set them to the viewer here
            viewer.state.x_display_unit = self.spectral_unit_selected
            # _handle_spectral_y_unit will call viewer.set_plot_axes()
            self._handle_spectral_y_unit()

        elif isinstance(viewer, BqplotImageView):
            # set the attribute display unit (contour and stretch units) for the new layer
            # NOTE: this assumes that all image data is coerced to surface brightness units
            layers = [lyr for lyr in msg.viewer.layers if lyr.layer.data.label == msg.data.label]
            self._handle_attribute_display_unit(self.sb_unit_selected, layers=layers)
            self._clear_cache('image_layers')

    def _on_slice_changed(self, msg):
        if self.config != "cubeviz":
            return
        self._cube_wave = u.Quantity(msg.value, msg.value_unit)

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
            # handle spectral y-unit first since that is a more apparent change to the user
            # and feels laggy if it is done later
            if self.spectral_y_type_selected == 'Flux':
                self._handle_spectral_y_unit()

            if len(self.angle_unit_selected):
                # NOTE: setting sb_unit_selected will call this method again with axis=='sb',
                # which in turn will call _handle_attribute_display_unit,
                # _handle_spectral_y_unit (if spectral_y_type_selected == 'Surface Brightness'),
                #  and send a second GlobalDisplayUnitChanged message for sb
                self.sb_unit_selected = _flux_to_sb_unit(self.flux_unit.selected,
                                                         self.angle_unit.selected)

        elif axis == 'angle':
            if len(self.flux_unit_selected):
                # NOTE: setting sb_unit_selected will call this method again with axis=='sb',
                # which in turn will call _handle_attribute_display_unit,
                # _handle_spectral_y_unit (if spectral_y_type_selected == 'Surface Brightness'),
                #  and send a second GlobalDisplayUnitChanged message for sb
                self.sb_unit_selected = _flux_to_sb_unit(self.flux_unit.selected,
                                                         self.angle_unit.selected)

        elif axis == 'sb':
            # handle spectral y-unit first since that is a more apparent change to the user
            # and feels laggy if it is done later
            if self.spectral_y_type_selected == 'Surface Brightness':
                self._handle_spectral_y_unit()

            self._handle_attribute_display_unit(self.sb_unit_selected)

        # custom axes downstream can override _on_unit_selected if anything needs to be
        # processed before the GlobalDisplayUnitChanged message is broadcast

        # axis (first) argument will be one of: spectral, flux, angle, sb, time
        self.hub.broadcast(GlobalDisplayUnitChanged(axis,
                           msg.new, sender=self))

    @observe('spectral_y_type_selected')
    def _handle_spectral_y_unit(self, *args):
        """
        When the spectral_y_type is changed, or the unit corresponding to the
        currently selected spectral_y_type is changed, update the y-axis of
        the spectrum viewer with the new unit, and then emit a
        GlobalDisplayUnitChanged message to notify
        """
        yunit = _valid_glue_display_unit(self.spectral_y_unit, self.spectrum_viewer, 'y')
        if self.spectrum_viewer.state.y_display_unit == yunit:
            self.spectrum_viewer.set_plot_axes()
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
        Update the per-layer attribute display unit in glue for image viewers
        (updating stretch and contour units).
        """
        if layers is None:
            layers = self.image_layers

        for layer in layers:
            # DQ layer doesn't play nicely with this attribute
            if "DQ" in layer.layer.label or isinstance(layer.layer, GroupedSubset):
                continue
            elif ("flux" not in [str(c) for c in layer.layer.components]
                    or u.Unit(layer.layer.get_component("flux").units).physical_type != 'surface brightness'):  # noqa
                continue
            if hasattr(layer.state, 'attribute_display_unit'):
                if self.config == "cubeviz":
                    ctx = u.set_enabled_equivalencies(
                        u.spectral() + u.spectral_density(self._cube_wave) +
                        _eqv_flux_to_sb_pixel() +
                        _eqv_pixar_sr(layer.layer.meta.get('_pixel_scale_factor', 1)))
                else:
                    ctx = nullcontext()
                with ctx:
                    layer.state.attribute_display_unit = _valid_glue_display_unit(
                        attr_unit, layer, 'attribute')
