from glue.core.subset import RangeSubsetState
import numpy as np

from glue.core import Data

from jdaviz import Application
from ..moment_maps import MomentMap


URL = 'https://stsci.box.com/shared/static/28a88k1qfipo4yxc4p4d40v4axtlal8y.fits'


def test_moment_calculation(spectral_cube_wcs):

    app = Application()
    dc = app.data_collection
    dc.append(Data(x=np.ones((3, 4, 5)), label='test', coords=spectral_cube_wcs))

    mm = MomentMap(app=app)

    mm.selected_data = 'test'
    mm.n_moment = 0
    mm.vue_calculate_moment(None)

    print(dc[1].get_object())

    assert mm.moment_available
    assert dc[1].label == 'Moment 0: test'
    assert dc[1].get_object().shape == (4, 5)


def test_wavelength_selection(spectral_cube_wcs):

    app = Application(configuration='cubeviz')
    # TODO: replace this by dummy data
    from astropy.utils.data import download_file
    fn = download_file(URL, cache=True)
    app.load_data(fn)
    data = app.data_collection[0]
    # TODO: this dummy data does not work, it doesn't create viewers
    # data = Data(x=np.ones((3, 4, 5)), label='test', coords=spectral_cube_wcs)
    # app.add_data(data, 'test')

    mm = MomentMap(app=app)

    subset_state = RangeSubsetState(5e-7, 6.0e-7, data.coordinate_components[3])
    app.data_collection.new_subset_group(subset_state=subset_state, label='x')
    mm.vue_list_subsets(None)   # this normally gets called from the UI
    mm.selected_subset = 'x'
    assert abs(mm.spectral_min - 5e-7) < 1e-6
    assert abs(mm.spectral_max - 6e-7) < 1e-6
