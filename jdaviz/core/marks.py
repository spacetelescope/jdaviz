import numpy as np

from astropy import units as u
from bqplot import LinearScale
from bqplot.marks import Lines, Label, Scatter
from glue.core import HubListener
from specutils import Spectrum

from jdaviz.core.events import GlobalDisplayUnitChanged
from jdaviz.core.events import (SliceToolStateMessage, LineIdentifyMessage,
                                SpectralMarksChangedMessage,
                                RedshiftMessage)
from jdaviz.core.unit_conversion_utils import (all_flux_unit_conversion_equivs,
                                               check_if_unit_is_per_solid_angle,
                                               flux_conversion_general)


__all__ = ['OffscreenLinesMarks', 'BaseSpectrumVerticalLine', 'SpectralLine',
           'SliceIndicatorMarks', 'ShadowMixin', 'ShadowLine', 'ShadowLabelFixedY',
           'PluginMark', 'LinesAutoUnit', 'PluginLine', 'PluginScatter',
           'LineAnalysisContinuum', 'LineAnalysisContinuumCenter',
           'LineAnalysisContinuumLeft', 'LineAnalysisContinuumRight',
           'LineUncertainties', 'ScatterMask', 'SelectedSpaxel', 'MarkersMark',
           'CatalogMark', 'FootprintOverlay', 'ApertureMark', 'DistanceMeasurement',
           'DistanceLabel']

accent_color = "#c75d2c"


class OffscreenLinesMarks(HubListener):
    def __init__(self, viewer):
        self.viewer = viewer

        viewer.state.add_callback("x_min", lambda x_min: self._update_counts())
        viewer.state.add_callback("x_max", lambda x_max: self._update_counts())

        viewer.session.hub.subscribe(self, RedshiftMessage,
                                     handler=self._update_counts)
        viewer.session.hub.subscribe(self, SpectralMarksChangedMessage,
                                     handler=self._update_counts)

        self.left = Label(text=[''], x=[0.02], y=[0.8],
                          scales={'x': LinearScale(min=0, max=1),
                                  'y': LinearScale(min=0, max=1)},
                          colors=['gray'], default_size=12,
                          align='start')
        self.right = Label(text=[''], x=[0.98], y=[0.8],
                           scales={'x': LinearScale(min=0, max=1),
                                   'y': LinearScale(min=0, max=1)},
                           colors=['gray'], default_size=12,
                           align='end')

        self._update_counts()

    @property
    def marks(self):
        return [self.left, self.right]

    def _update_counts(self, *args):
        oob_left, oob_right = 0, 0
        for m in self.viewer.figure.marks:
            if isinstance(m, SpectralLine):
                if m.x[0] < self.viewer.state.x_min:
                    oob_left += 1
                elif m.x[0] > self.viewer.state.x_max:
                    oob_right += 1
        self.left.text = [f'\u25c0 {oob_left}' if oob_left > 0 else '']
        self.right.text = [f'{oob_right} \u25b6' if oob_right > 0 else '']


class PluginMarkCollection:
    # This class allows for the creation of plugin preview marks across viewers
    def __init__(self, mark_cls, shadow_cls=None, shadow_kwargs={}, **mark_kwargs):
        self.mark_cls = mark_cls
        self.shadow_cls = shadow_cls
        self.shadow_kwargs = shadow_kwargs
        self.mark_kwargs = mark_kwargs
        self.shadow_marks = {}
        self.marks = {}

    @property
    def marks_list(self):
        return list(self.marks.values())

    def marks_for_viewers(self, viewers):
        for viewer in viewers:
            if viewer not in self.marks:
                # Create a new mark for the given viewer
                mark = self.mark_cls(viewer=viewer, **self.mark_kwargs)
                self.marks[viewer] = mark
                if self.shadow_cls is not None:
                    shadow_kwargs = {k: v.marks_for_viewers([viewer])[0]
                                     if isinstance(v, PluginMarkCollection) else v
                                     for k, v in self.shadow_kwargs.items()}
                    shadow = self.shadow_cls(shadowing=mark, **shadow_kwargs)
                    self.shadow_marks[viewer] = shadow
                    viewer.figure.marks += [shadow]
                viewer.figure.marks += [mark]
                viewer.figure.send_state('marks')
        return [self.marks[viewer] for viewer in viewers]

    def clear_if_not_in_viewers(self, viewers):
        for viewer, mark in self.marks.items():
            if viewer not in viewers:
                # Clear the mark if the viewer is not in the list
                mark.clear()
                mark.visible = False

    def clear(self):
        for mark in self.marks.values():
            mark.clear()

    def update_xy(self, x, y, viewers):
        for mark in self.marks_for_viewers(viewers):
            mark.update_xy(x, y)
            mark.visible = True
        self.clear_if_not_in_viewers(viewers)

    def set_for_viewers(self, name, value, viewers):
        for mark in self.marks_for_viewers(viewers):
            setattr(mark, name, value)

    def __setattr__(self, name, value):
        if name in ('plugin', 'mark_cls', 'shadow_cls',
                    'shadow_kwargs', 'mark_kwargs',
                    'shadow_marks', 'marks'):
            super().__setattr__(name, value)
        else:
            # pass on to all stored marks
            for mark in self.marks.values():
                setattr(mark, name, value)


class PluginMark:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.xunit = None
        self.yunit = None
        # whether to update existing marks when global display units are changed
        self.auto_update_units = True
        self.hub.subscribe(self, GlobalDisplayUnitChanged,
                           handler=self._on_global_display_unit_changed)

        if self.xunit is None:
            self.set_x_unit()
        if self.yunit is None:
            self.set_y_unit()

    @property
    def hub(self):
        return self.viewer.hub

    def update_xy(self, x, y):
        # If x and y are not in the previous units, they should be provided as quantities
        if hasattr(x, 'value'):
            xunit = x.unit
            x = x.value
        else:
            xunit = None
        self.x = np.asarray(x)
        if xunit is not None:
            self.xunit = u.Unit(xunit)

        if hasattr(y, 'value'):
            yunit = y.unit
            y = y.value
        else:
            yunit = None
        self.y = np.asarray(y)
        if yunit is not None:
            self.yunit = u.Unit(yunit)

    def append_xy(self, x, y):
        self.x = np.append(self.x, x)
        self.y = np.append(self.y, y)

    def set_x_unit(self, unit=None):
        if unit is None:
            if not hasattr(self.viewer.state, 'x_display_unit'):
                if isinstance(self.viewer, ('Spectrum2DViewer', 'MosvizProfile2DView')):
                    # x-unit of 2d spectrum viewers are always in pixels
                    unit = u.pix
                elif self.viewer.data() and hasattr(self.viewer.data()[0], 'spectral_axis'):
                    unit = self.viewer.data()[0].spectral_axis.unit
                else:
                    return
            else:
                unit = self.viewer.state.x_display_unit
        unit = u.Unit(unit)

        if self.xunit is not None and not np.all([s == 0 for s in self.x.shape]):
            x = (self.x * self.xunit).to_value(unit, u.spectral())
            self.xunit = unit
            self.x = x
        self.xunit = unit

    def set_y_unit(self, unit=None):
        if unit is None:
            if not hasattr(self.viewer.state, 'y_display_unit'):
                if isinstance(self.viewer, ('Spectrum2DViewer', 'MosvizProfile2DView')):
                    # y-unit of 2d spectrum viewers are always in pixels
                    unit = u.pix
                elif self.viewer.data() and hasattr(self.viewer.data()[0], 'flux'):
                    unit = self.viewer.data()[0].flux.unit
                else:
                    return
            else:
                unit = self.viewer.state.y_display_unit
        unit = u.Unit(unit)

        # spectrum y-values in viewer have already been converted, don't convert again
        # if a spectral_y_type is changed, just update the unit
        if self.yunit is not None and check_if_unit_is_per_solid_angle(self.yunit) != check_if_unit_is_per_solid_angle(unit):  # noqa
            self.yunit = unit
            return

        if self.yunit is not None and not np.all([s == 0 for s in self.y.shape]):  # noqa
            if self.viewer.default_class is Spectrum:
                if self.xunit is None:
                    return
                spec = self.viewer.state.reference_data.get_object(cls=Spectrum)

                pixar_sr = spec.meta.get('PIXAR_SR', None)
                # if x is all the same value, then we either have a vertical line mark or
                # a flat spectrum, in either case we can use a single value for the spectral
                # density equivalency.
                if len(np.unique(self.x)) == 1 and (len(self.x) != len(self.y)):
                    wave = self.x[0] * self.xunit
                else:
                    wave = self.x * self.xunit
                equivs = all_flux_unit_conversion_equivs(pixar_sr, wave)
                y = flux_conversion_general(self.y, self.yunit, unit,
                                            equivs, with_unit=False)

            self.y = y

        self.yunit = unit

    def _on_global_display_unit_changed(self, msg):
        if not self.auto_update_units:
            return
        unit = msg.unit
        if (msg.axis in ('spectral', 'spectral_y') and
                self.viewer.__class__.__name__ in ('Spectrum2DViewer',
                                                   'MosvizProfile2DView')):
            # then we want to ignore the change to spectral unit as these viewers
            # are always in pixel units on the x-axis
            unit = u.pix
        if self.viewer.__class__.__name__ in ('Spectrum1DViewer',
                                              'Spectrum2DViewer',
                                              'CubevizProfileView',
                                              'MosvizProfileView',
                                              'MosvizProfile2DView'):

            axis_map = {'spectral': 'x', 'spectral_y': 'y'}
        else:
            return
        axis = axis_map.get(msg.axis, None)
        if axis is not None:
            scale = self.scales.get(axis, None)
            # if PluginMark mark is LinearScale(0, 1), prevent it from entering unit conversion
            # machinery so it maintains it's position in viewer.
            if isinstance(scale, LinearScale) and (scale.min, scale.max) == (0, 1):
                return

            getattr(self, f'set_{axis}_unit')(unit)

    def clear(self):
        self.update_xy([], [])


class BaseSpectrumVerticalLine(Lines, PluginMark, HubListener):
    def __init__(self, viewer, x, **kwargs):
        self.viewer = viewer

        # the location of the marker will need to update automatically if the
        # underlying data changes (through a unit conversion, for example)
        if hasattr(viewer.state, 'reference_data'):
            viewer.state.add_callback("reference_data",
                                      self._update_reference_data)

        scales = viewer.scales

        # Lines.__init__ will set self.x
        super().__init__(x=[x, x], y=[0, 1],
                         scales={'x': scales['x'], 'y': LinearScale(min=0, max=1)},
                         **kwargs)

    def _update_reference_data(self, reference_data):
        # don't update x units before initialization or in rampviz
        if reference_data is None or self.viewer.jdaviz_app.config == 'rampviz':
            return

        self._update_unit(reference_data.get_object(cls=Spectrum).spectral_axis.unit)

    def _update_unit(self, new_unit):
        # the x-units may have changed.  We want to convert the internal self.x
        # from self.xunit to the new units (x_all.unit)
        if self.xunit is None:
            self.xunit = new_unit
            return
        if new_unit == self.xunit:
            return
        old_quant = self.x[0]*self.xunit
        x = old_quant.to_value(new_unit, equivalencies=u.spectral())
        self.x = [x, x]
        self.xunit = new_unit


class SpectralLine(BaseSpectrumVerticalLine):
    """
    Subclass on bqplot Lines, mostly so that we can erase spectral lines
    by eliminating any SpectralLines objects from a figures marks list. Also
    lets us do wavelength redshifting here on mark creation.
    """
    def __init__(self, viewer, rest_value, redshift=0, name=None, **kwargs):
        self._rest_value = rest_value
        self._identify = False
        self.name = name

        # table_index is same as name_rest elsewhere
        self.table_index = kwargs.pop("table_index", None)

        # setting redshift will set self.x and enable the obs_value property,
        # but to do that we need x_unit set first (would normally be assigned
        # in the super init)
        self.xunit = u.Unit(viewer.state.x_display_unit)
        self.redshift = redshift

        viewer.session.hub.subscribe(self, LineIdentifyMessage,
                                     handler=self._process_identify_change)

        super().__init__(viewer=viewer, x=self.obs_value, stroke_width=1,
                         fill='none', close_path=False, **kwargs)

    @property
    def name_rest(self):
        return self.table_index

    @property
    def rest_value(self):
        return self._rest_value

    @property
    def obs_value(self):
        return self.x[0]

    def set_x_unit(self, unit=None):
        prev_unit = self.xunit
        super().set_x_unit(unit=unit)
        self._rest_value = (self._rest_value * prev_unit).to_value(unit, u.spectral())

    @property
    def redshift(self):
        return self._redshift

    @redshift.setter
    def redshift(self, redshift):
        self._redshift = redshift
        if str(self.xunit.physical_type) == 'length':
            obs_value = self._rest_value*(1+redshift)
        elif str(self.xunit.physical_type) == 'frequency':
            obs_value = self._rest_value/(1+redshift)
        else:
            # catch all for anything else (wavenumber, energy, etc)
            rest_angstrom = (self._rest_value*self.xunit).to_value(u.Angstrom,
                                                                   equivalencies=u.spectral())
            obs_angstrom = rest_angstrom*(1+redshift)
            obs_value = (obs_angstrom*u.Angstrom).to_value(self.xunit,
                                                           equivalencies=u.spectral())
        self.x = [obs_value, obs_value]

    @property
    def identify(self):
        return self._identify

    @identify.setter
    def identify(self, identify):
        if not isinstance(identify, bool):  # pragma: no cover
            raise TypeError("identify must be of type bool")

        self._identify = identify
        self.stroke_width = 3 if identify else 1

    def _process_identify_change(self, msg):
        self.identify = msg.name_rest == self.table_index

    def _update_unit(self, new_unit):
        if self.xunit is None:
            self.xunit = new_unit
            return
        if new_unit == self.xunit:
            return

        old_quant = self._rest_value*self.xunit
        self._rest_value = old_quant.to_value(new_unit, equivalencies=u.spectral())
        # re-compute self.x from current redshift (instead of converting that as well)
        self.redshift = self._redshift
        self.xunit = new_unit


class SliceIndicatorMarks(BaseSpectrumVerticalLine, HubListener):
    """Subclass on bqplot Lines to handle slice/wavelength indicator.
    """
    def __init__(self, viewer, value=0, **kwargs):
        self._viewer = viewer
        self._value = None
        self._oob = False  # out-of-bounds, either False, 'left', or 'right'
        self._active = False
        # TODO: new viewers need to respect plugin settings
        self._show_if_inactive = True
        self._show_value = True

        viewer.state.add_callback("x_min", lambda x_min: self._value_handle_oob(update_label=True))
        viewer.state.add_callback("x_max", lambda x_max: self._value_handle_oob(update_label=True))
        viewer.session.hub.subscribe(self, SliceToolStateMessage,
                                     handler=self._on_change_state)

        super().__init__(viewer=viewer,
                         x=[value, value],
                         stroke_width=2,
                         marker='diamond',
                         fill='none', close_path=False,
                         labels=['slice'], labels_visibility='none', **kwargs)

        self.value = value

        # instead of using the Lines label which is limited, we'll use a Label object which
        # will follow the x-coordinate of the slice indicator line, with a fixed y-value
        # (in axes-units) and will flip its alignment depending on whether the line is on the
        # left or right side of the axes.
        self.label = ShadowLabelFixedY(viewer, self, shadow_traits=[], default_size=12, y=0.95)

        # default to the initial state of the tool since we can't control if this will
        # happen before or after the initialization of the tool
        tool_active = self.viewer.toolbar.active_tool_id == 'jdaviz:selectslice'
        self._on_change_state({'active': tool_active})

    @property
    def marks(self):
        return [self, self.label]

    def _on_global_display_unit_changed(self, msg):
        # Updating the value is handled by the plugin itself, need to update unit string.
        if msg.axis in ["spectral", "x"]:
            self.xunit = msg.unit
        self._update_label()

    def _value_handle_oob(self, x=None, update_label=False):
        if x is None:
            x = self.value
        else:
            self._value = x
        x_min, x_max = self._viewer.state.x_min, self._viewer.state.x_max
        if x_min is None or x_max is None:
            self.x = [x, x]
            return
        x_range = x_max - x_min
        padding_fig = 0.01
        padding = padding_fig * x_range
        x_min += padding
        x_max -= padding
        # ensure y-scale has been set (we'll only be overriding x, but scatter viewers complain
        # if y-scale is not set)
        self.scales.setdefault('y', LinearScale(min=0, max=1))
        if x < x_min:
            self.x = [padding_fig, padding_fig]
            self.scales = {**self.scales, 'x': LinearScale(min=0, max=1)}
            self.line_style = 'dashed'
            self._oob = 'left'
        elif x > x_max:
            self.x = [1-padding_fig, 1-padding_fig]
            self.scales = {**self.scales, 'x': LinearScale(min=0, max=1)}
            self.line_style = 'dashed'
            self._oob = 'right'
        else:
            self.x = [x, x]
            self.scales = {**self.scales, 'x': self._viewer.scales['x']}
            self.line_style = 'solid'
            self._oob = False
        if update_label:
            self._update_label()

    def _update_colors_opacities(self):
        # orange (accent) if active, import button blue otherwise (see css in main_styles.vue)
        if not self._show_if_inactive and not self._active:
            self.label.visible = False
            self.visible = False
            return

        self.visible = True
        self.label.visible = self._show_value
        self.colors = ["#c75109" if self._active else "#007BA1"]
        self.opacities = [1.0 if self._active else 0.9]

    def _on_change_state(self, msg={}):
        if isinstance(msg, dict):
            changes = msg
        else:
            if msg.viewer is not None and msg.viewer != self.viewer:
                return
            changes = msg.change

        for k, v in changes.items():
            if k == 'active':
                self._active = v
            elif k == 'show_indicator':
                self._show_if_inactive = v
            elif k == 'show_value':
                self._show_value = v

        self._update_colors_opacities()

    def _update_label(self):
        def _formatted_value(value):
            power = abs(np.log10(value))
            if power >= 3:
                # use scientific notation
                return f'{value:0.4e}'
            else:
                return f'{value:0.4f}'

        valuestr = _formatted_value(self.value)
        xunit = str(self.xunit) if self.xunit is not None else ''
        # U+00A0 is a blank space, U+25C0 a left arrow triangle, and U+25B6 a right arrow triangle
        if self._oob == 'left':
            self.labels = [f'\u00A0 \u25c0 {valuestr} {xunit} \u00A0']  # noqa
        elif self._oob == 'right':
            self.labels = [f'{valuestr} {xunit} \u25b6 \u00A0']
        else:
            self.labels = [f'\u00A0 {valuestr} {xunit} \u00A0']

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value_handle_oob(value, update_label=True)


class ShadowMixin:
    """Mixin class to propagate traits from one mark object to another.
    Anything in ``sync_traits`` will be mirrored directly from
    ``shadowing`` to the shadowed object.

    Can manually override ``_on_shadowing_changed`` for more advanced logic cases.
    """
    def _get_id(self, mark):
        return getattr(mark, '_model_id', None)

    def _setup_shadowing(self, shadowing, sync_traits=[], other_traits=[]):
        """
        sync_traits: traits to set now, and mirror any changes to shadowing in the future
        other_trait: traits to set now, but not mirror in the future
        """
        if not hasattr(self, '_shadowing'):
            self._shadowing = {}
            self._sync_traits = {}
        shadowing_id = self._get_id(shadowing)
        self._shadowing[shadowing_id] = shadowing
        self._sync_traits[shadowing_id] = sync_traits

        # sync initial values
        for attr in sync_traits + other_traits:
            self._on_shadowing_changed({'name': attr,
                                        'new': getattr(shadowing, attr),
                                        'owner': shadowing})

        # subscribe to future changes
        shadowing.observe(self._on_shadowing_changed)

    def _on_shadowing_changed(self, change):
        if change['name'] in self._sync_traits.get(self._get_id(change.get('owner')), []):
            setattr(self, change['name'], change['new'])
        return


class ShadowLine(Lines, HubListener, ShadowMixin):
    """Create a white shadow line around another line
    to help make it standout on top of other lines.
    """
    def __init__(self, shadowing, shadow_width=1, **kwargs):
        self._shadow_width = shadow_width
        super().__init__(scales=shadowing.scales,
                         stroke_width=shadowing.stroke_width+shadow_width if shadowing.stroke_width else 0, # noqa
                         marker_size=shadowing.marker_size+shadow_width if shadowing.marker_size else 0, # noqa
                         colors=[kwargs.pop('color', 'white')],
                         **kwargs)

        self._setup_shadowing(shadowing,
                              ['scales', 'x', 'y', 'visible', 'line_style', 'marker'],
                              ['stroke_width', 'marker_size'])


class ShadowLabelFixedY(Label, ShadowMixin):
    """Label whose position shadows that of a parent ``shadowing``
    line and will flip alignment based on whether it is left or
    right of the center of the viewer.
    """
    def __init__(self, viewer, shadowing, shadow_traits=['visible'],
                 y=0.95, point_index=0, **kwargs):
        super().__init__(**kwargs)
        self._viewer = viewer
        self.y = [y]
        self.scales['y'] = LinearScale(min=0, max=1)
        self._point_index = point_index
        self._setup_shadowing(shadowing,
                              shadow_traits,
                              ['x', 'scales', 'labels', 'colors'])

        viewer.state.add_callback("x_min", lambda x_min: self._update_align())
        viewer.state.add_callback("x_max", lambda x_max: self._update_align())

    def _force_redraw(self):
        # TODO: bug in bqplot that change in align/colors traitlet doesn't update immediately,
        # we'll get around it in the meantime by just forcing the Label to see a change to the
        # text traitlet
        text = self.text
        self.text = ['']
        self.text = text

    def _update_align(self):
        if not isinstance(self.scales.get('x'), LinearScale):
            return
        # determine alignment automatically
        if self.scales['x'].min == 0 and self.scales['x'].max == 1:
            # then we're in axes units, so just check position compared to 0.5
            is_to_right = self.x[0] > 0.5
        else:
            # then we're in data units, so check position compared to the median of the axes limits
            is_to_right = self.x[0] > (self._viewer.state.x_min + self._viewer.state.x_max) / 2.

        if is_to_right and self.align != 'end':
            self.align = 'end'
            # force redraw by re-updating label
            self._force_redraw()
        if not is_to_right and self.align != 'start':
            self.align = 'start'
            # force redraw by re-updating label
            self._force_redraw()

    def _on_shadowing_changed(self, change):
        super()._on_shadowing_changed(change)
        if change['name'] == 'labels':
            self.text = [change['new'][self._point_index]]
        elif change['name'] in ('x', 'colors'):
            setattr(self, change['name'], [change['new'][self._point_index]])
            if change['name'] == 'colors':
                # bqplot bug that won't notice change to colors, manually force re-draw
                self._force_redraw()
        elif change['name'] == 'scales':
            self.scales = {**self.scales, 'x': change['new']['x']}

        if change['name'] in ('x', 'scales'):
            # then the position of the label on the plot has changed, so re-determine whether
            # it should be aligned to the left or right
            self._update_align()


class LinesAutoUnit(PluginMark, Lines, HubListener):
    def __init__(self, viewer, *args, **kwargs):
        self.viewer = viewer
        super().__init__(*args, **kwargs)


class PluginLine(Lines, PluginMark, HubListener):
    def __init__(self, viewer, x=[], y=[], **kwargs):
        self.viewer = viewer
        # color is same blue as import button
        kwargs.setdefault('colors', [accent_color])
        self.label = kwargs.get('label')
        super().__init__(x=x, y=y, scales=kwargs.pop('scales', viewer.scales), **kwargs)


class PluginScatter(Scatter, PluginMark, HubListener):
    def __init__(self, viewer, x=[], y=[], **kwargs):
        self.viewer = viewer
        # default color is same blue as import button
        kwargs.setdefault('colors', [accent_color])
        super().__init__(x=x, y=y, scales=kwargs.pop('scales', viewer.scales), **kwargs)


class LineAnalysisContinuum(PluginLine):
    def __init__(self, *args, **kwargs):
        # units do not need to be updated because the plugin itself reruns
        # the computation and automatically changes the arrays themselves
        self.auto_update_units = kwargs.pop('auto_update_units', False)
        super().__init__(*args, **kwargs)


class LineAnalysisContinuumCenter(LineAnalysisContinuum):
    def __init__(self, viewer, x=[], y=[], **kwargs):
        super().__init__(viewer, x, y, **kwargs)
        self.stroke_width = 1


class LineAnalysisContinuumLeft(LineAnalysisContinuum):
    def __init__(self, viewer, x=[], y=[], **kwargs):
        super().__init__(viewer, x, y, **kwargs)
        self.stroke_width = 5


class LineAnalysisContinuumRight(LineAnalysisContinuumLeft):
    pass


class LineUncertainties(LinesAutoUnit):
    def __init__(self, viewer, *args, **kwargs):
        super().__init__(viewer, *args, **kwargs)


class ScatterMask(Scatter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class SelectedSpaxel(Lines):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class MarkersMark(PluginScatter):
    def __init__(self, viewer, **kwargs):
        kwargs.setdefault('marker', 'circle')
        super().__init__(viewer, **kwargs)


class CatalogMark(PluginScatter):
    def __init__(self, viewer, **kwargs):
        kwargs.setdefault('marker', 'circle')
        super().__init__(viewer, **kwargs)


class FootprintOverlay(PluginLine):
    def __init__(self, viewer, overlay, **kwargs):
        self._overlay = overlay
        kwargs.setdefault('stroke_width', 1)
        kwargs.setdefault('close_path', True)
        kwargs.setdefault('opacities', [0.8])
        kwargs.setdefault('fill', 'inside')
        kwargs.setdefault('fill_opacities', [0.2])
        super().__init__(viewer, **kwargs)

    @property
    def overlay(self):
        return self._overlay

    def set_selected_style(self, is_selected):
        if not isinstance(is_selected, bool):  # pragma: no cover
            raise TypeError("is_selected must be of type bool")

        self.stroke_width = 4 if is_selected else 1


class ApertureMark(PluginLine):
    def __init__(self, viewer, id, **kwargs):
        self._id = id
        super().__init__(viewer, **kwargs)


class HistogramMark(Lines):
    def __init__(self, min_max_value, scales, **kwargs):
        # Vertical line in LinearScale
        y = [0, 1]
        colors = [accent_color]
        line_style = "solid"
        super().__init__(x=min_max_value, y=y, scales=scales, colors=colors, line_style=line_style,
                         **kwargs)


class DistanceLabel(Label, PluginMark, HubListener):
    """A specialized bqplot Label for use with the DistanceMeasurement tool.

    This class inherits from the Jdaviz PluginMark to integrate with the
    application's hub and event system, but overrides the unit conversion
    methods to prevent the label's pixel-based coordinates from being
    erroneously converted.
    """

    def __init__(self, viewer, x, y, text, **kwargs):
        self.viewer = viewer
        kwargs.setdefault('align', 'middle')
        kwargs.setdefault('baseline', 'middle')
        kwargs.setdefault('x_offset', 0)
        kwargs.setdefault('y_offset', 0)

        super().__init__(x=[x], y=[y], text=[text], scales=viewer.scales, **kwargs)
        self.auto_update_units = False

    def set_x_unit(self, unit=None):
        pass

    def set_y_unit(self, unit=None):
        pass

    def update_position(self, x, y, text):
        self.x = [x]
        self.y = [y]
        self.text = [text]


class DistanceMeasurement:
    """A composite mark that displays a line between two points with a
    dynamically rotated and offset label showing the distance.

    This class manages a collection of bqplot marks (a Line and two Labels
    for text and its halo) to create a single, cohesive measurement indicator
    in a viewer. The core logic in the `update_points` method handles the
    positioning, rotation, and offsetting of the label to ensure it remains
    parallel to the line while avoiding intersection.
    """

    def __init__(self, viewer, x0, y0, x1, y1, text=""):
        self.viewer = viewer
        self.endpoints = None

        self.line = Lines(
            x=[],
            y=[],
            scales=viewer.scales,
            colors=[accent_color],
            stroke_width=2
        )

        anchor_x, anchor_y = (x0 + x1) / 2, (y0 + y1) / 2

        self.label_shadow = DistanceLabel(
            viewer, anchor_x, anchor_y, text,
            colors=['white'],
            stroke='white',
            stroke_width=5,
            font_weight='bold',
            default_size=15
        )

        self.label_text = DistanceLabel(
            viewer, anchor_x, anchor_y, text,
            colors=[accent_color],
            font_weight='bold',
            default_size=15
        )

        self.visible = True
        self.update_points(x0, y0, x1, y1, text)

    @property
    def marks(self):
        # The shadow must be listed before the text to be drawn underneath.
        return [self.line, self.label_shadow, self.label_text]

    @property
    def visible(self):
        return self.line.visible

    @visible.setter
    def visible(self, visible):
        # Update visibility for all marks.
        self.line.visible = visible
        self.label_shadow.visible = visible
        self.label_text.visible = visible

    def update_points(self, x0, y0, x1, y1, text=""):
        x0_v = getattr(x0, 'value', x0)
        y0_v = getattr(y0, 'value', y0)
        x1_v = getattr(x1, 'value', x1)
        y1_v = getattr(y1, 'value', y1)

        self.line.x = [x0_v, x1_v]
        self.line.y = [y0_v, y1_v]

        mid_x = (x0_v + x1_v) / 2
        mid_y = (y0_v + y1_v) / 2

        dx_data = x1_v - x0_v
        dy_data = y1_v - y0_v

        angle_rad = np.arctan2(-dy_data, dx_data)
        angle_deg = np.rad2deg(angle_rad)

        # Check for the special case of a perfect diagonal line.
        # A small tolerance is used for floating-point comparison.
        if abs(abs(dx_data) - abs(dy_data)) < 1e-9:
            x_offset_float = 0
            y_offset_float = 30

        else:
            offset_distance = 10
            line_length_data = np.sqrt(dx_data**2 + dy_data**2)

            if line_length_data > 0:
                perp_dx = -dy_data
                perp_dy = dx_data
                x_offset_float = (perp_dx / line_length_data) * offset_distance
                y_offset_float = (perp_dy / line_length_data) * offset_distance
            else:
                x_offset_float = 0
                y_offset_float = -offset_distance

            # Determine text offset direction based on the center of the viewer
            x_scale = self.viewer.scales.get('x')
            y_scale = self.viewer.scales.get('y')

            # Check if the viewer scales and their min/max values are available
            if (x_scale is not None and y_scale is not None and
                    x_scale.min is not None and x_scale.max is not None and
                    y_scale.min is not None and y_scale.max is not None):

                viewer_center_x = (x_scale.min + x_scale.max) / 2
                viewer_center_y = (y_scale.min + y_scale.max) / 2
                pos_vec_x = mid_x - viewer_center_x
                pos_vec_y = mid_y - viewer_center_y
                if (pos_vec_x * perp_dx + pos_vec_y * perp_dy) > 0:
                    x_offset_float *= -1
                    y_offset_float *= -1

        x_offset_int = int(round(x_offset_float))
        y_offset_int = int(round(y_offset_float))

        # Normalize the display angle for readability
        if abs(angle_deg) > 90:
            angle_deg -= 180 * np.sign(angle_deg)

        for label in (self.label_shadow, self.label_text):
            label.update_position(mid_x, mid_y, text)
            label.rotate_angle = angle_deg
            label.x_offset = x_offset_int
            label.y_offset = -y_offset_int
