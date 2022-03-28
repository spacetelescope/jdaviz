from astropy import units as u
from bqplot.marks import Lines, Scatter
from glue.core import HubListener
from specutils import Spectrum1D

from jdaviz.core.events import SliceToolStateMessage, LineIdentifyMessage


class BaseSpectrumVerticalLine(Lines, HubListener):
    def __init__(self, viewer, x, **kwargs):
        # we'll store the current units so that we can automatically update the
        # positioning on a change to the x-units
        self._x_unit = viewer.state.reference_data.get_object(cls=Spectrum1D).spectral_axis.unit

        # the location of the marker will need to update automatically if the
        # underlying data changes (through a unit conversion, for example)
        viewer.state.add_callback("reference_data",
                                  self._update_reference_data)

        # keep the y values at the y-limits of the plot
        viewer.state.add_callback("y_min", lambda y_min: self._update_ys(y_min=y_min))
        viewer.state.add_callback("y_max", lambda y_max: self._update_ys(y_max=y_max))

        scales = viewer.scales
        # _update_ys will set self.y
        self._update_ys(scales['y'].min, scales['y'].max)

        # Lines.__init__ will set self.x
        super().__init__(x=[x, x], y=self.y, scales=scales, **kwargs)

    def _update_ys(self, y_min=None, y_max=None):
        self.y = [y_min if y_min is not None else self.y[0],
                  y_max if y_max is not None else self.y[1]]

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


class SliceIndicator(BaseSpectrumVerticalLine, HubListener):
    """
    Subclass on bqplot Lines to handle slice/wavelength indicator
    """
    def __init__(self, viewer, slice=0, **kwargs):
        self._active = False
        self._show_if_inactive = True

        self.slice = slice
        x_all = viewer.data()[0].spectral_axis
        # _update_data will set self._x_all, self._x_unit, self.x
        self._update_data(x_all)

        viewer.session.hub.subscribe(self, SliceToolStateMessage,
                                     handler=self._on_change_state)

        super().__init__(viewer=viewer,
                         x=self.x[0],
                         stroke_width=2,
                         marker='diamond',
                         fill='none', close_path=False,
                         labels=['slice'], labels_visibility='label', **kwargs)

        # default to the initial state of the tool since we can't control if this will
        # happen before or after the initialization of the tool
        self._on_change_state({'active': True})

    def _slice_to_x(self, slice=0):
        if not isinstance(slice, int):
            raise TypeError(f"slice must be of type int, not {type(slice)}")
        return self._x_all[slice]

    def _update_colors_opacities(self):
        # orange (accent) if active, import button blue otherwise (see css in app.vue)
        if not self._show_if_inactive and not self._active:
            self.visible = False
            return

        self.visible = True
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
            elif k == 'setting_show_indicator':
                self._show_if_inactive = v
            elif k == 'setting_show_wavelength':
                self.labels_visibility = 'label' if v else 'none'

        self._update_colors_opacities()

    def _update_label(self):
        self.labels = [f'\u00A0{self.x[0]:0.4e} {self._x_unit}']

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
            self.x = [x_coord, x_coord]
            self._update_label()

    def _update_data(self, x_all):
        # we want to preserve slice number, so we'll do a bit more than the
        # default unit-conversion in the base class
        self._x_all = x_all.value
        self._x_unit = str(x_all.unit)
        x_coord = self._slice_to_x(self.slice)
        self.x = [x_coord, x_coord]
        if self.labels_visibility == 'label':
            # update label with new value/unit
            self._update_label()


class Shadow(Lines, HubListener):
    _sync_traits = ['scales', 'x', 'y', 'visible', 'line_style', 'marker']

    def __init__(self, shadowing, shadow_width=1, **kwargs):
        self._shadow_width = shadow_width
        super().__init__(scales=shadowing.scales,
                         stroke_width=shadowing.stroke_width+shadow_width if shadowing.stroke_width else 0, # noqa
                         marker_size=shadowing.marker_size+shadow_width if shadowing.marker_size else 0, # noqa
                         colors=[kwargs.pop('color', 'white')],
                         **kwargs)

        # sync initial values
        for attr in self._sync_traits:
            setattr(self, attr, getattr(shadowing, attr))

        # keep values synced when traits on shadowing object change
        shadowing.observe(self._on_shadowing_changed)

    def _on_shadowing_changed(self, change):
        attr = change['name']
        if attr[0] in ['stroke_width', 'marker_size']:
            value = change['new'] + self._shadow_width if change['new'] else 0
        elif attr not in self._sync_traits:
            return
        else:
            value = change['new']

        setattr(self, attr, value)


class LineAnalysisContinuum(Lines, HubListener):
    def __init__(self, viewer, x=[], y=[], **kwargs):
        # we do not need to worry about the x-units changing since the stats
        # need to be re-computed on unit conversion anyways (which will
        # trigger updates to x and y from the line analysis plugin)

        # color is same blue as import button
        super().__init__(x=x, y=y, colors=["#007BA1"], scales=viewer.scales, **kwargs)

    def update_xy(self, x, y):
        self.x = x
        self.y = y


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
