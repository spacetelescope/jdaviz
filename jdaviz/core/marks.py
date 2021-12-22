from astropy import units as u
from bqplot.marks import Lines
from glue.core import HubListener
from specutils import Spectrum1D


class BaseSpectrumVerticalLine(Lines, HubListener):
    def __init__(self, viewer, x, **kwargs):
        # we'll store the current units so that we can automatically update the
        # positioning on a change to the x-units
        self._x_unit = viewer.state.reference_data.get_object().spectral_axis.unit

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
        self.name = name

        # TODO: do we need table_index anymore?
        self.table_index = kwargs.pop("table_index", None)

        # setting redshift will set self.x and enable the obs_value property,
        # but to do that we need x_unit set first (would normally be assigned
        # in the super init)
        self._x_unit = viewer.state.reference_data.get_object().spectral_axis.unit
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

    def _update_data(self, x_all):
        new_unit = x_all.unit
        if new_unit == self._x_unit:
            return

        old_quant = self._rest_value*self._x_unit
        self._rest_value = old_quant.to_value(new_unit, equivalencies=u.spectral())
        # re-compute self.x from current redshift (instead of converting that as well)
        self.redshift = self._redshift
        self._x_unit = new_unit



class SliceIndicator(Lines):
    """
    Subclass on bqplot Lines to handle slice/wavelength indicator
    """
    def __init__(self, x_all, scales, slice=0, **kwargs):
        self.update_data(x_all)
        x_coord = self.slice_to_x(slice)
        y_coords = [scales['y'].min, scales['y'].max]
        super().__init__(x=[x_coord, x_coord], y=y_coords, scales=scales,
                         stroke_width=2, opacities=[0.6],
                         fill='none', close_path=False, **kwargs)

    def update_data(self, x_all):
        self._x_all = x_all

    def slice_to_x(self, slice=0):
        return self._x_all[slice]

    def update_slice(self, slice):
        x_coord = self.slice_to_x(slice)
        self.x = [x_coord, x_coord]

#    def show(self):
#        self.visible = True

#    def hide(self):
#        self.visible = False
