import base64
import os
import uuid
from functools import partial

import numpy as np
from astropy.timeseries import TimeSeries
from glue.core.component import Component
from glue.core.coordinates import Coordinates
from glue.core.data import Data

from jdaviz.core.registries import data_parser_registry

__all__ = ['parse_data']


@data_parser_registry("timeviz-data-parser")
def parse_data(app, file_obj, data_label=None, time_column='time', flux_column='sap_flux',
               show_in_viewer=True, **kwargs):
    """Parse a time series into Timeviz.

    Parameters
    ----------
    app : `~jdaviz.app.Application`
        The application-level object used to reference the viewers.

    file_obj : str or `~astropy.timeseries.TimeSeries`
        Time series filename or object to parse.

    data_label : str
        The label to be applied to the Glue data component.

    time_column : str
        Column name containing the time information.
        This field is case-sensitive.

    flux_column : str
        Column name containing the flux corresponding to ``time_column``.
        This field is case-sensitive.

    show_in_viewer : bool
        Show data in viewer.

    **kwargs
        Additional keywords to be passed into :meth:`astropy.timeseries.TimeSeries.read`.
        This is only used if ``file_obj`` is a filename.

    Raises
    ------
    NotImplementedError
        Unsupported input format.

    """
    if isinstance(file_obj, str):
        ts = TimeSeries.read(file_obj, time_column=time_column, **kwargs)
        if data_label is None:
            data_label = os.path.splitext(os.path.basename(file_obj))[0]
    elif not isinstance(file_obj, TimeSeries):
        raise NotImplementedError(f'Timeviz cannot parse {file_obj}')
    elif data_label is None:
        data_label = f'timeviz_data|{str(base64.b85encode(uuid.uuid4().bytes), "utf-8")}'

    # TODO: Is there a better way to do this?
    time_coord = Time1D_MJD_Coordinates(ts[time_column].mjd)

    flux_col = ts[flux_column]
    flux_comp = Component.autotyped(flux_col.value, units=flux_col.unit.to_string())

    data = Data(label=data_label)
    data.meta.update(ts.meta)
    data.coords = time_coord
    data.add_component(component=flux_comp, label='flux')

    data._preferred_translation = True  # Triggers custom viewer.set_plot_axes()

    app.add_data(data, data_label)
    if show_in_viewer:
        app.add_data_to_viewer(f"{app.config}-0", data_label)


class Time1D_MJD_Coordinates(Coordinates):
    """Map MJD to pixel indices."""

    def __init__(self, mjd_array, *args, **kwargs):
        super().__init__(n_dim=1)
        i_arr = np.arange(len(mjd_array))
        self._func = partial(np.interp, xp=i_arr, fp=mjd_array,
                             left=np.nan, right=np.nan)
        self._invfunc = partial(np.interp, xp=mjd_array, fp=i_arr,
                                left=np.nan, right=np.nan)

    def pixel_to_world_values(self, *args):
        # This should take N arguments (where N is the number of dimensions
        # in your dataset) and assume these are 0-based pixel coordinates,
        # then return N world coordinates with the same shape as the input.
        return self._func(args)

    def world_to_pixel_values(self, *args):
        # This should take N arguments (where N is the number of dimensions
        # in your dataset) and assume these are 0-based pixel coordinates,
        # then return N world coordinates with the same shape as the input.
        return self._invfunc(args)

    @property
    def world_axis_units(self):
        # Returns an iterable of strings given the units of the world
        # coordinates for each axis.
        return ['day']

    @property
    def world_axis_names(self):
        # Returns an iterable of strings given the names of the world
        # coordinates for each axis.
        return ['MJD']  # https://github.com/glue-viz/glue/issues/2283
