import os

import pytest
from astropy.nddata import CCDData

from jdaviz.configs.cubeviz.plugins.moment_maps.moment_maps import MomentMap


@pytest.mark.filterwarnings('ignore:No observer defined on WCS')
def test_moment_calculation(cubeviz_helper, spectrum1d_cube, tmpdir):
    dc = cubeviz_helper.app.data_collection
    cubeviz_helper.load_data(spectrum1d_cube, data_label='test')

    mm = MomentMap(app=cubeviz_helper.app)
    mm.dataset_selected = 'test[FLUX]'

    mm.n_moment = 0  # Collapsed sum, will get back 2D spatial image
    assert mm.results_label == 'moment 0'

    mm.add_results.viewer.selected = 'mask-viewer'
    mm.vue_calculate_moment()

    assert mm.moment_available
    assert dc[1].label == 'moment 0'
    mv_data = cubeviz_helper.app.get_viewer('mask-viewer').data()
    # by default, will overwrite the previous entry (so only one data entry)
    assert len(mv_data) == 1
    assert mv_data[0].label == 'moment 0'

    assert len(dc.links) == 8

    # label should remain unchanged but raise overwrite warnings
    assert mm.results_label == 'moment 0'
    assert mm.results_label_overwrite is True

    result = dc[1].get_object(cls=CCDData)
    assert result.shape == (4, 2)  # Cube shape is (2, 2, 4)

    # FIXME: Need spatial WCS, see https://github.com/spacetelescope/jdaviz/issues/1025
    assert dc[1].coords is None

    # Make sure coordinate display still works
    flux_viewer = cubeviz_helper.app.get_viewer('flux-viewer')
    flux_viewer.on_mouse_or_key_event({'event': 'mousemove', 'domain': {'x': 0, 'y': 0}})
    assert flux_viewer.state.slices == (0, 0, 1)
    assert flux_viewer.label_mouseover.pixel == 'x=00.0 y=00.0'
    assert flux_viewer.label_mouseover.value == '+8.00000e+00 Jy'  # Slice 0 has 8 pixels, this is Slice 1  # noqa
    assert flux_viewer.label_mouseover.world_ra_deg == '204.9997755346'
    assert flux_viewer.label_mouseover.world_dec_deg == '27.0000999998'

    assert mm.filename == 'moment0_test_FLUX.fits'  # Auto-populated on calculate.
    mm.filename = str(tmpdir.join(mm.filename))  # But we want it in tmpdir for testing.
    mm.vue_save_as_fits()
    assert os.path.isfile(mm.filename)

    # Does not allow overwrite.
    with pytest.raises(OSError, match='already exists'):
        mm.vue_save_as_fits()

    mm.n_moment = 1
    assert mm.results_label == 'moment 1'
    assert mm.results_label_overwrite is False
    mm.vue_calculate_moment()

    assert dc[2].label == 'moment 1'

    assert len(dc.links) == 10

    # Coordinate display should be unaffected.
    assert flux_viewer.label_mouseover.pixel == 'x=00.0 y=00.0'
    assert flux_viewer.label_mouseover.value == '+8.00000e+00 Jy'  # Slice 0 has 8 pixels, this is Slice 1  # noqa
    assert flux_viewer.label_mouseover.world_ra_deg == '204.9997755346'
    assert flux_viewer.label_mouseover.world_dec_deg == '27.0000999998'
