import pytest

from jdaviz.configs.cubeviz.plugins.slice.slice import Slice


@pytest.mark.filterwarnings('ignore:No observer defined on WCS')
def test_slice(cubeviz_helper, spectrum1d_cube):
    app = cubeviz_helper.app
    sl = Slice(app=app)
    app.add_data(spectrum1d_cube, 'test')
    app.add_data_to_viewer("spectrum-viewer", "test")
    app.add_data_to_viewer("flux-viewer", "test")

    # sample cube only has 2 slices with wavelengths [4.62280007e-07 4.62360028e-07] m
    assert sl.slider == 1
    cubeviz_helper.select_slice(0)
    assert sl.slider == 0

    with pytest.raises(
            TypeError,
            match="slice must be an integer"):
        cubeviz_helper.select_slice("blah")

    with pytest.raises(
            ValueError,
            match="slice must be positive"):
        cubeviz_helper.select_slice(-5)

    cubeviz_helper.select_wavelength(4.62360028e-07)
    assert sl.slider == 1
