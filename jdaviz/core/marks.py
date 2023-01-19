import numpy as np

from astropy import units as u
from bqplot import LinearScale
from bqplot.marks import Lines, Label, Scatter
from copy import deepcopy
from glue.core import HubListener
from specutils import Spectrum1D

from jdaviz.core.events import (SliceToolStateMessage, LineIdentifyMessage,
                                SpectralMarksChangedMessage,
                                RedshiftMessage)

__all__ = ['OffscreenLinesMarks', 'BaseSpectrumVerticalLine', 'SpectralLine',
           'SliceIndicatorMarks', 'ShadowMixin', 'ShadowLine', 'ShadowLabelFixedY',
           'PluginMark', 'PluginLine', 'PluginScatter',
           'LineAnalysisContinuum', 'LineAnalysisContinuumCenter',
           'LineAnalysisContinuumLeft', 'LineAnalysisContinuumRight',
           'LineUncertainties', 'ScatterMask', 'SelectedSpaxel']


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
                          scales={'x': LinearScale(min=0, max=1), 'y': LinearScale(min=0, max=1)},
                          colors=['gray'], default_size=12,
                          align='start')
        self.right = Label(text=[''], x=[0.98], y=[0.8],
                           scales={'x': LinearScale(min=0, max=1), 'y': LinearScale(min=0, max=1)},
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


class BaseSpectrumVerticalLine(Lines, HubListener):
    def __init__(self, viewer, x, **kwargs):
        # we'll store the current units so that we can automatically update the
        # positioning on a change to the x-units
        self._x_unit = viewer.state.reference_data.get_object(cls=Spectrum1D).spectral_axis.unit

        # the location of the marker will need to update automatically if the
        # underlying data changes (through a unit conversion, for example)
        viewer.state.add_callback("reference_data",
                                  self._update_reference_data)

        scales = viewer.scales

        # Lines.__init__ will set self.x
        super().__init__(x=[x, x], y=[0, 1],
                         scales={'x': scales['x'], 'y': LinearScale(min=0, max=1)},
                         **kwargs)

    def _update_reference_data(self, reference_data):
        if reference_data is None:
            return
        self._update_data(reference_data.get_object(cls=Spectrum1D).spectral_axis)

    def _update_data(self, x_all):
        # the x-units may have changed.  We want to convert the internal self.x
        # from self._x_unit to the new units (x_all.unit)
        new_unit = x_all.unit
        if new_unit == self._x_unit:
            return
        old_quant = self.x[0]*self._x_unit
        x = old_quant.to_value(x_all.unit, equivalencies=u.spectral())
        self.x = [x, x]
        self._x_unit = new_unit


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
        self._x_unit = viewer.state.reference_data.get_object(cls=Spectrum1D).spectral_axis.unit
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

    @property
    def redshift(self):
        return self._redshift

    @redshift.setter
    def redshift(self, redshift):
        self._redshift = redshift
        if str(self._x_unit.physical_type) == 'length':
            obs_value = self._rest_value*(1+redshift)
        elif str(self._x_unit.physical_type) == 'frequency':
            obs_value = self._rest_value/(1+redshift)
        else:
            # catch all for anything else (wavenumber, energy, etc)
            rest_angstrom = (self._rest_value*self._x_unit).to_value(u.Angstrom,
                                                                     equivalencies=u.spectral())
            obs_angstrom = rest_angstrom*(1+redshift)
            obs_value = (obs_angstrom*u.Angstrom).to_value(self._x_unit,
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

    def _update_data(self, x_all):
        new_unit = x_all.unit
        if new_unit == self._x_unit:
            return

        old_quant = self._rest_value*self._x_unit
        self._rest_value = old_quant.to_value(new_unit, equivalencies=u.spectral())
        # re-compute self.x from current redshift (instead of converting that as well)
        self.redshift = self._redshift
        self._x_unit = new_unit


class SliceIndicatorMarks(BaseSpectrumVerticalLine, HubListener):
    """Subclass on bqplot Lines to handle slice/wavelength indicator.
    """
    def __init__(self, viewer, slice=0, **kwargs):
        self._viewer = viewer
        self._oob = False  # out-of-bounds, either False, 'left', or 'right'
        self._active = False
        self._show_if_inactive = True
        self._show_wavelength = True

        self.slice = slice
        x_all = viewer.data()[0].spectral_axis
        # _update_data will set self._x_all, self._x_unit, self.x
        self._update_data(x_all)

        viewer.state.add_callback("x_min", lambda x_min: self._handle_oob(update_label=True))
        viewer.state.add_callback("x_max", lambda x_max: self._handle_oob(update_label=True))
        viewer.session.hub.subscribe(self, SliceToolStateMessage,
                                     handler=self._on_change_state)

        super().__init__(viewer=viewer,
                         x=self.x[0],
                         stroke_width=2,
                         marker='diamond',
                         fill='none', close_path=False,
                         labels=['slice'], labels_visibility='none', **kwargs)

        self._handle_oob()

        # instead of using the Lines label which is limited, we'll use a Label object which
        # will follow the x-coordinate of the slice indicator line, with a fixed y-value
        # (in axes-units) and will flip its alignment depending on whether the line is on the
        # left or right side of the axes.
        self.label = ShadowLabelFixedY(viewer, self, shadow_traits=[], default_size=12, y=0.95)

        # default to the initial state of the tool since we can't control if this will
        # happen before or after the initialization of the tool
        self._on_change_state({'active': True})

    @property
    def marks(self):
        return [self, self.label]

    def _handle_oob(self, x_coord=None, update_label=False):
        if x_coord is None:
            x_coord = self._slice_to_x(self.slice)
        x_min, x_max = self._viewer.state.x_min, self._viewer.state.x_max
        if x_min is None or x_max is None:
            self.x = [x_coord, x_coord]
            return
        x_range = x_max - x_min
        padding_fig = 0.01
        padding = padding_fig * x_range
        x_min += padding
        x_max -= padding
        if x_coord < x_min:
            self.x = [padding_fig, padding_fig]
            self.scales = {**self.scales, 'x': LinearScale(min=0, max=1)}
            self.line_style = 'dashed'
            self._oob = 'left'
        elif x_coord > x_max:
            self.x = [1-padding_fig, 1-padding_fig]
            self.scales = {**self.scales, 'x': LinearScale(min=0, max=1)}
            self.line_style = 'dashed'
            self._oob = 'right'
        else:
            self.x = [x_coord, x_coord]
            self.scales = {**self.scales, 'x': self._viewer.scales['x']}
            self.line_style = 'solid'
            self._oob = False
        if update_label:
            self._update_label()

    def _slice_to_x(self, slice=0):
        if not isinstance(slice, int):
            raise TypeError(f"slice must be of type int, not {type(slice)}")
        return self._x_all[slice]

    def _update_colors_opacities(self):
        # orange (accent) if active, import button blue otherwise (see css in app.vue)
        if not self._show_if_inactive and not self._active:
            self.label.visible = False
            self.visible = False
            return

        self.visible = True
        self.label.visible = self._show_wavelength
        self.colors = ["#c75109" if self._active else "#007BA1"]
        self.opacities = [1.0 if self._active else 0.9]

    def _on_change_state(self, msg):
        if isinstance(msg, dict):
            changes = msg
        else:
            changes = msg.change

        for k, v in changes.items():
            if k == 'active':
                self._active = v
            elif k == 'show_indicator':
                self._show_if_inactive = v
            elif k == 'show_wavelength':
                self._show_wavelength = v

        self._update_colors_opacities()

    def _update_label(self):
        # U+00A0 is a blank space, U+25C0 a left arrow triangle, and U+25B6 a right arrow triangle
        if self._oob == 'left':
            self.labels = [f'\u00A0 \u25c0 {self._slice_to_x(self.slice):0.4e} {self._x_unit} \u00A0']  # noqa
        elif self._oob == 'right':
            self.labels = [f'{self._slice_to_x(self.slice):0.4e} {self._x_unit} \u25b6 \u00A0']
        else:
            self.labels = [f'\u00A0 {self._slice_to_x(self.slice):0.4e} {self._x_unit} \u00A0']

    @property
    def slice(self):
        return self._slice

    @slice.setter
    def slice(self, slice):
        self._slice = slice
        # if this is within the init, the data may not have been set yet,
        # in which case we'll just set self._slice for the first time, but
        # do not need to update self.x or label (yet)
        if hasattr(self, '_x_all'):
            x_coord = self._slice_to_x(slice)
            self._handle_oob(x_coord)
            self._update_label()

    def _update_data(self, x_all):
        # we want to preserve slice number, so we'll do a bit more than the
        # default unit-conversion in the base class
        self._x_all = x_all.value
        self._x_unit = str(x_all.unit)
        x_coord = self._slice_to_x(self.slice)
        self._handle_oob(x_coord)
        if self.labels_visibility == 'label':
            # update label with new value/unit
            self._update_label()


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


class ShadowSpatialSpectral(Lines, HubListener, ShadowMixin):
    """
    Shadow the mark of a spatial subset collapsed spectrum, with the mask from a spectral subset,
    and the styling from the spatial subset.
    """
    def __init__(self, spatial_spectrum_mark, spectral_subset_mark):
        # spatial_spectrum_mark: Lines mark corresponding to the spatially-collapsed spectrum
        # from a spatial subset
        # spectral_subset_mark: Lines mark on the FULL cube corresponding to the glue-highlight
        # of the spectral subset
        super().__init__(scales=spatial_spectrum_mark.scales, marker=None)

        self._spatial_mark_id = self._get_id(spatial_spectrum_mark)
        self._setup_shadowing(spatial_spectrum_mark,
                              ['scales', 'y', 'visible', 'line_style'],
                              ['x'])

        self._spectral_mark_id = self._get_id(spectral_subset_mark)
        self._setup_shadowing(spectral_subset_mark,
                              ['stroke_width', 'x', 'y', 'visible', 'opacities', 'colors'])

    @property
    def spatial_spectrum_mark(self):
        return self._shadowing[self._spatial_mark_id]

    @property
    def spectral_subset_mark(self):
        return self._shadowing[self._spectral_mark_id]

    def _on_shadowing_changed(self, change):
        if hasattr(self, '_spectral_mark_id'):
            if change['name'] == 'y':
                # at initial setup, the arrays may not be populated yet
                if self.spatial_spectrum_mark.y.shape == self.spectral_subset_mark.y.shape:
                    # force a copy or else we'll overwrite the mask to the spatial mark!
                    change['new'] = deepcopy(self.spatial_spectrum_mark.y)
                    change['new'][np.isnan(self.spectral_subset_mark.y)] = np.nan

            elif change['name'] == 'visible':
                # only show if BOTH shadowing marks are set to visible
                change['new'] = self.spectral_subset_mark.visible and self.spatial_spectrum_mark.visible  # noqa

        return super()._on_shadowing_changed(change)


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


class PluginMark():
    def update_xy(self, x, y):
        self.x = np.asarray(x)
        self.y = np.asarray(y)

    def append_xy(self, x, y):
        self.x = np.append(self.x, x)
        self.y = np.append(self.y, y)

    def clear(self):
        self.update_xy([], [])


class PluginLine(Lines, PluginMark, HubListener):
    def __init__(self, viewer, x=[], y=[], **kwargs):
        # color is same blue as import button
        super().__init__(x=x, y=y, colors=["#007BA1"], scales=viewer.scales, **kwargs)


class PluginScatter(Scatter, PluginMark, HubListener):
    def __init__(self, viewer, x=[], y=[], **kwargs):
        # color is same blue as import button
        super().__init__(x=x, y=y, colors=["#007BA1"], scales=viewer.scales, **kwargs)


class LineAnalysisContinuum(PluginLine):
    pass


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


class LineUncertainties(Lines):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class ScatterMask(Scatter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class SelectedSpaxel(Lines):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
