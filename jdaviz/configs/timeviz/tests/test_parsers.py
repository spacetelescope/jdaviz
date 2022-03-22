import numpy as np
import pytest
import warnings
from astropy import units as u
from astropy.timeseries import TimeSeries
from astropy.utils.data import get_pkg_data_filename
from numpy.testing import assert_allclose

from jdaviz.configs.timeviz.plugins.parsers import Time1D_MJD_Coordinates


def test_parse_timeseries(timeviz_helper):
    ts1 = TimeSeries(time_start='2016-03-22T12:30:31', time_delta=3 * u.s, n_samples=5,
                     data={'flux': [1, 4, 1, 5, 6] * u.nJy})
    timeviz_helper.load_data(ts1, flux_column='flux')
    assert len(timeviz_helper.app.data_collection) == 1

    data = timeviz_helper.app.data_collection[0]
    comp = data.get_component('flux')
    assert data.label.startswith('timeviz_data')
    assert isinstance(data.coords, Time1D_MJD_Coordinates)
    assert_allclose(comp.data, [1, 4, 1, 5, 6])
    assert comp.units == 'nJy'


@pytest.mark.remote_data
def test_parse_kepler_slc(timeviz_helper):
    filename = get_pkg_data_filename('timeseries/kplr010666592-2009131110544_slc.fits',
                                     package='astropy')
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')  # Ignore FITS warnings
        timeviz_helper.load_data(filename, format='kepler.fits')
        ts = TimeSeries.read(filename, format='kepler.fits')
    assert len(timeviz_helper.app.data_collection) == 1

    time_col = ts['time']
    flux_col = ts['sap_flux']

    data = timeviz_helper.app.data_collection[0]
    comp = data.get_component('flux')
    assert data.label == 'contents'
    assert_allclose(comp.data, flux_col.value)
    assert comp.units == flux_col.unit.to_string()

    coord = data.coords
    idx = np.arange(comp.data.size)
    time_mjd = coord.pixel_to_world_values(idx)[0]
    assert_allclose(time_mjd, time_col.mjd)
    assert_allclose(coord.world_to_pixel_values(time_mjd)[0], idx)  # Roundtrip


def test_parse_invalid(timeviz_helper):
    with pytest.raises(NotImplementedError, match='Timeviz cannot parse'):
        timeviz_helper.load_data([1, 4, 1, 5, 6])
