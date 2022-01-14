from bqplot.marks import Lines

from glue.core import HubListener


class BaseSpectrumVerticalLine(Lines, HubListener):
    def __init__(self, viewer, x, **kwargs):
        # we'll store the current units so that we can automatically update the
        # positioning on a change to the x-units
        self._x_unit = viewer.state.reference_data.get_object().spectral_axis.unit

        # the location of the marker will need to update automatically if the
        # underlying data changes (through a unit conversion, for example)
        viewer.state.add_callback("reference_data",
                                  lambda reference_data: self._update_data(reference_data.get_object().spectral_axis)) # noqa

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

    def _update_data(self, x_all):
        # the x-units may have changed.  We want to convert the internal self.x
        # from self._x_unit to the new units (x_all.unit)
        new_unit = x_all.unit
        if new_unit == self._x_unit:
            return
        x = (self.x[0] * self._x_unit).to(x_all.unit).value
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
        self.name = name

        # TODO: do we need table_index anymore?
        self.table_index = kwargs.pop("table_index", None)

        # setting redshift will set self.x and enable the obs_value property
        self.redshift = redshift

        super().__init__(viewer=viewer, x=self.obs_value, stroke_width=1,
                         fill='none', close_path=False, **kwargs)

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
        obs_value = self._rest_value*(1+redshift)
        self.x = [obs_value, obs_value]
