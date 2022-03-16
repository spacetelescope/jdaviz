import os

import pytest
from astropy.nddata import CCDData

from jdaviz.configs.cubeviz.plugins.moment_maps.moment_maps import MomentMap


@pytest.mark.filterwarnings('ignore:No observer defined on WCS')
def test_moment_calculation(cubeviz_helper, spectrum1d_cube, tmpdir):
    app = cubeviz_helper.app
    dc = app.data_collection
    app.add_data(spectrum1d_cube, 'test[FLUX]')

    mm = MomentMap(app=app)
    mm._subset_selected = 'None'
    mm._on_data_updated(None)

    mm._on_data_selected({'new': 'test[FLUX]'})

    mm.n_moment = 0  # Collapsed sum, will get back 2D spatial image
    mm.vue_calculate_moment()

    assert mm.moment_available
    assert dc[1].label == 'Moment 0: test[FLUX]'

    assert len(dc.links) == 8

    result = dc[1].get_object(cls=CCDData)
    assert result.shape == (2, 4)  # Cube shape is (2, 2, 4)

    # FIXME: Need spatial WCS, see https://github.com/spacetelescope/jdaviz/issues/1025
    assert dc[1].coords is None

    assert mm.filename == 'moment0_test_FLUX.fits'  # Auto-populated on calculate.
    mm.filename = str(tmpdir.join(mm.filename))  # But we want it in tmpdir for testing.
    mm.vue_save_as_fits()
    assert os.path.isfile(mm.filename)

    # Does not allow overwrite.
    with pytest.raises(OSError, match='already exists'):
        mm.vue_save_as_fits()

    mm.n_moment = 1
    mm.vue_calculate_moment()

    assert dc[2].label == 'Moment 1: test[FLUX]'

    assert len(dc.links) == 10
