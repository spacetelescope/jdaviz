import pytest
from astropy.nddata import CCDData


@pytest.mark.filterwarnings('ignore:No observer defined on WCS')
def test_spectrum_at_spaxel(cubeviz_helper, spectrum1d_cube):
    app = cubeviz_helper.app
    cubeviz_helper.load_data(spectrum1d_cube, data_label='test')

    flux_viewer = cubeviz_helper.app.get_viewer("flux-viewer")
    spectrum_viewer = cubeviz_helper.app.get_viewer("spectrum-viewer")

    # Set the active tool to spectrumperspaxel
    flux_viewer.toolbar.active_tool = flux_viewer.toolbar.tools['jdaviz:spectrumperspaxel']
    x = 1
    y = 1
    assert len(flux_viewer.figure.marks) == 2
    assert len(spectrum_viewer.data()) == 1

    # Click on pixel location
    flux_viewer.toolbar.active_tool.on_mouse_event({'event': 'click', 'domain': {'x': x, 'y': y}})
    assert len(flux_viewer.figure.marks) == 3
    assert len(spectrum_viewer.data()) == 2
    assert app.data_collection[-1].label == "test_at_pixel"
    assert app.data_collection[-1].meta["reference_data"] == "test"
    assert app.data_collection[-1].meta["created_from_pixel"] == f"({x}, {y})"

    # Deselect tool
    flux_viewer.toolbar.active_tool = None
    assert len(flux_viewer.figure.marks) == 2


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

    # Click on pixel location
    flux_viewer.toolbar.active_tool.on_mouse_event({'event': 'click', 'domain': {'x': x, 'y': y}})
    assert len(flux_viewer.figure.marks) == 2
    assert len(spectrum_viewer.data()) == 0

    # Deselect tool
    flux_viewer.toolbar.active_tool = None
    assert len(flux_viewer.figure.marks) == 2
