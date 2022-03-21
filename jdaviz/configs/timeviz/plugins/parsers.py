import base64
import os
import uuid

from astropy.timeseries import TimeSeries
from glue.core.component import Component, DateTimeComponent
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

    # FIXME: Cannot be promoted to float type deep in Glue?
    # time_comp = DateTimeComponent(ts[time_column].datetime64)
    time_comp = Component.autotyped(ts[time_column].mjd)

    flux_col = ts[flux_column]
    flux_comp = Component.autotyped(flux_col.value, units=flux_col.unit.to_string())
    data = Data(label=data_label)
    data.meta.update(ts.meta)
    data.add_component(component=flux_comp, label='flux')
    data.add_component(component=time_comp, label='time')

    data._preferred_translation = True  # Triggers custom viewer.set_plot_axes()

    app.add_data(data, data_label)
    if show_in_viewer:
        app.add_data_to_viewer(f"{app.config}-0", data_label)
