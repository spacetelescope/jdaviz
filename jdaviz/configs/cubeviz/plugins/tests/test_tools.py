import pytest
from astropy.nddata import CCDData

from regions import RectanglePixelRegion


@pytest.mark.filterwarnings('ignore:No observer defined on WCS')
def test_spectrum_at_spaxel(cubeviz_helper, spectrum1d_cube):
    cubeviz_helper.load_data(spectrum1d_cube, data_label='test')

    flux_viewer = cubeviz_helper.app.get_viewer("flux-viewer")
    spectrum_viewer = cubeviz_helper.app.get_viewer("spectrum-viewer")

    # Set the active tool to spectrumperspaxel
    flux_viewer.toolbar.active_tool = flux_viewer.toolbar.tools['jdaviz:spectrumperspaxel']
    x = 1
    y = 1
    assert len(flux_viewer.figure.marks) == 2
    assert len(spectrum_viewer.data()) == 1

    # Click on spaxel location
    flux_viewer.toolbar.active_tool.on_mouse_event(
        {'event': 'click', 'domain': {'x': x, 'y': y}, 'altKey': False})
    assert len(flux_viewer.figure.marks) == 3
    assert len(spectrum_viewer.data()) == 2

    # Check that a new subset was created
    subsets = cubeviz_helper.app.get_subsets_from_viewer('flux-viewer')
    reg = subsets.get('Subset 1')
    assert len(subsets) == 1
    assert isinstance(reg, RectanglePixelRegion)

    # Deselect tool
    flux_viewer.toolbar.active_tool = None
    assert len(flux_viewer.figure.marks) == 3


def test_spectrum_at_spaxel_altkey_true(cubeviz_helper, spectrum1d_cube):
    cubeviz_helper.load_data(spectrum1d_cube, data_label='test')

    flux_viewer = cubeviz_helper.app.get_viewer("flux-viewer")
    spectrum_viewer = cubeviz_helper.app.get_viewer("spectrum-viewer")

    # Set the active tool to spectrumperspaxel
    flux_viewer.toolbar.active_tool = flux_viewer.toolbar.tools['jdaviz:spectrumperspaxel']
    x = 1
    y = 1
    assert len(flux_viewer.figure.marks) == 2
    assert len(spectrum_viewer.data()) == 1

    # Click on spaxel location
    flux_viewer.toolbar.active_tool.on_mouse_event(
        {'event': 'click', 'domain': {'x': x, 'y': y}, 'altKey': False})
    assert len(flux_viewer.figure.marks) == 3
    assert len(spectrum_viewer.data()) == 2

    # Check that subset was created
    subsets = cubeviz_helper.app.get_subsets_from_viewer('flux-viewer')
    reg = subsets.get('Subset 1')
    assert len(subsets) == 1
    assert isinstance(reg, RectanglePixelRegion)

    # Using altKey should create a new subset
    x = 2
    y = 2
    flux_viewer.toolbar.active_tool.on_mouse_event(
        {'event': 'click', 'domain': {'x': x, 'y': y}, 'altKey': True})
    assert len(flux_viewer.figure.marks) == 4
    assert len(spectrum_viewer.data()) == 3

    subsets = cubeviz_helper.app.get_subsets_from_viewer('flux-viewer')
    reg2 = subsets.get('Subset 2')
    assert len(subsets) == 2
    assert isinstance(reg2, RectanglePixelRegion)


def test_spectrum_at_spaxel_with_2d(cubeviz_helper):
    # Use 2D image, which should not work with the tool
    x = CCDData([[1, 2, 3], [4, 5, 6]], unit='adu')

    app = cubeviz_helper.app
    app.data_collection["test"] = x
    app.add_data_to_viewer("flux-viewer", "test")

    flux_viewer = cubeviz_helper.app.get_viewer("flux-viewer")
    spectrum_viewer = cubeviz_helper.app.get_viewer("spectrum-viewer")

    # Set the active tool to spectrumperspaxel
    flux_viewer.toolbar.active_tool = flux_viewer.toolbar.tools['jdaviz:spectrumperspaxel']
    x = 1
    y = 1
    assert len(flux_viewer.figure.marks) == 2
    assert len(spectrum_viewer.data()) == 0

    # Click on spaxel location
    flux_viewer.toolbar.active_tool.on_mouse_event(
        {'event': 'click', 'domain': {'x': x, 'y': y}, 'altKey': False})
    assert len(flux_viewer.figure.marks) == 3
    assert len(spectrum_viewer.data()) == 0

    # Deselect tool
    flux_viewer.toolbar.active_tool = None
    assert len(flux_viewer.figure.marks) == 3
