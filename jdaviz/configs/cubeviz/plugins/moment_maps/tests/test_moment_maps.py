import pytest
from astropy.nddata import CCDData

from jdaviz.configs.cubeviz.plugins.moment_maps.moment_maps import MomentMap


@pytest.mark.filterwarnings('ignore:No observer defined on WCS')
def test_moment_calculation(cubeviz_helper, spectrum1d_cube):
    app = cubeviz_helper.app
    dc = app.data_collection
    app.add_data(spectrum1d_cube, 'test')

    mm = MomentMap(app=app)
    mm._subset_selected = 'None'
    mm._on_data_updated(None)

    mm._on_data_selected({'new': 'test'})
    mm._on_subset_selected({'new': None})

    mm.n_moment = 0  # Collapsed sum, will get back 2D spatial image
    mm.vue_calculate_moment()

    assert mm.moment_available
    assert dc[1].label == 'Moment 0: test'

    result = dc[1].get_object(cls=CCDData)
    assert result.shape == (4, 2)

    # FIXME: Need spatial WCS, see https://github.com/spacetelescope/jdaviz/issues/1025
    assert dc[1].coords is None
