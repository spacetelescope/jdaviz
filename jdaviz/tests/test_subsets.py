import astropy.units as u
from astropy.tests.helper import assert_quantity_allclose
import numpy as np
from glue.core import Data
from glue.core.roi import RectangularROI, XRangeROI, CircularROI
from glue.core.edit_subset_mode import OrMode
from numpy.testing import assert_allclose
from specutils import SpectralRegion
from regions import RectanglePixelRegion

from jdaviz.configs.default import SubsetPlugin


def test_region_from_subset_2d(cubeviz_helper):
    data = Data(flux=np.ones((128, 128)), label='Test 2D Flux')
    cubeviz_helper.app.data_collection.append(data)

    cubeviz_helper.app.add_data_to_viewer('flux-viewer', 'Test 2D Flux')

    cubeviz_helper.app.get_viewer('flux-viewer').apply_roi(RectangularROI(1, 3.5, -0.2, 3.3))

    subsets = cubeviz_helper.app.get_subsets_from_viewer('flux-viewer')
    reg = subsets.get('Subset 1')

    assert len(subsets) == 1
    assert isinstance(reg, RectanglePixelRegion)

    assert_allclose(reg.center.x, 2.25)
    assert_allclose(reg.center.x, 2.25)
    assert_allclose(reg.center.y, 1.55)
    assert_allclose(reg.width, 2.5)
    assert_allclose(reg.height, 3.5)


def test_region_from_subset_3d(cubeviz_helper):
    data = Data(flux=np.ones((128, 128, 256)), label='Test 3D Flux')
    cubeviz_helper.app.data_collection.append(data)

    subset_plugin = SubsetPlugin(app=cubeviz_helper.app)
    assert subset_plugin.subset_selected == "Create New"

    cubeviz_helper.app.add_data_to_viewer('flux-viewer', 'Test 3D Flux')

    cubeviz_helper.app.get_viewer('flux-viewer').apply_roi(RectangularROI(1, 3.5, -0.2, 3.3))

    subsets = cubeviz_helper.app.get_subsets_from_viewer('flux-viewer')
    reg = subsets.get('Subset 1')

    assert len(subsets) == 1
    assert isinstance(reg, RectanglePixelRegion)

    assert_allclose(reg.center.x, 2.25)
    assert_allclose(reg.center.x, 2.25)
    assert_allclose(reg.center.y, 1.55)
    assert_allclose(reg.width, 2.5)
    assert_allclose(reg.height, 3.5)

    assert subset_plugin.subset_selected == "Subset 1"
    assert subset_plugin.subset_types == [{"Subset type": "RectangularROI"}]
    assert subset_plugin.subset_definitions[0]["Xmin"] == 1
    assert subset_plugin.subset_definitions[0]["Xmax"] == 3.5
    assert subset_plugin.subset_definitions[0]["Ymin"] == -0.2
    assert subset_plugin.subset_definitions[0]["Ymax"] == 3.3

    # Circular Subset
    flux_viewer = cubeviz_helper.app.get_viewer("flux-viewer")
    # We set the active tool here to trigger a reset of the Subset state to "Create new"
    flux_viewer.toolbar.active_tool = flux_viewer.toolbar.tools['bqplot:circle']
    cubeviz_helper.app.get_viewer('flux-viewer').apply_roi(CircularROI(xc=3, yc=4, radius=2.4))
    assert subset_plugin.subset_selected == "Subset 2"
    assert subset_plugin.subset_types == [{"Subset type": "CircularROI"}]
    assert subset_plugin.subset_definitions[0]["X Center"] == 3
    assert subset_plugin.subset_definitions[0]["Y Center"] == 4
    assert subset_plugin.subset_definitions[0]["Radius"] == 2.4


def test_region_from_subset_profile(cubeviz_helper, spectral_cube_wcs):
    data = Data(flux=np.ones((128, 128, 256)), label='Test 1D Flux', coords=spectral_cube_wcs)
    subset_plugin = SubsetPlugin(app=cubeviz_helper.app)

    cubeviz_helper.app.data_collection.append(data)

    cubeviz_helper.app.add_data_to_viewer('spectrum-viewer', 'Test 1D Flux')

    cubeviz_helper.app.get_viewer("spectrum-viewer").apply_roi(XRangeROI(5, 15.5))

    subsets = cubeviz_helper.app.get_subsets_from_viewer('spectrum-viewer', subset_type='spectral')
    reg = subsets.get('Subset 1')

    assert len(subsets) == 1
    assert isinstance(reg, SpectralRegion)
    assert_quantity_allclose(reg.lower, 5.0 * u.Hz)
    assert_quantity_allclose(reg.upper, 15.0 * u.Hz)

    assert subset_plugin.subset_selected == "Subset 1"
    assert subset_plugin.subset_types == [{"Subset type": "Range"}]
    assert subset_plugin.subset_definitions[0]["Lower bound"] == 5
    assert subset_plugin.subset_definitions[0]["Upper bound"] == 15.5


def test_region_spectral_spatial(cubeviz_helper, spectral_cube_wcs):
    data = Data(flux=np.ones((128, 128, 256)), label='Test Flux', coords=spectral_cube_wcs)
    cubeviz_helper.app.data_collection.append(data)

    cubeviz_helper.app.add_data_to_viewer('spectrum-viewer', 'Test Flux')
    cubeviz_helper.app.add_data_to_viewer('flux-viewer', 'Test Flux')

    cubeviz_helper.app.get_viewer("spectrum-viewer").apply_roi(XRangeROI(5, 15.5))

    flux_viewer = cubeviz_helper.app.get_viewer("flux-viewer")
    # We set the active tool here to trigger a reset of the Subset state to "Create new"
    flux_viewer.toolbar.active_tool = flux_viewer.toolbar.tools['bqplot:rectangle']
    flux_viewer.apply_roi(RectangularROI(1, 3.5, -0.2, 3.3))

    subsets = cubeviz_helper.app.get_subsets_from_viewer('spectrum-viewer', subset_type='spectral')
    reg = subsets.get('Subset 1')

    assert len(subsets) == 1
    assert isinstance(reg, SpectralRegion)

    assert_quantity_allclose(reg.lower, 5.0 * u.Hz)
    assert_quantity_allclose(reg.upper, 15 * u.Hz)

    subsets = cubeviz_helper.app.get_subsets_from_viewer('flux-viewer', subset_type='spatial')
    reg = subsets.get('Subset 2')

    assert len(subsets) == 1
    assert isinstance(reg, RectanglePixelRegion)
    assert_allclose(reg.center.x, 2.25)
    assert_allclose(reg.center.x, 2.25)
    assert_allclose(reg.center.y, 1.55)
    assert_allclose(reg.width, 2.5)
    assert_allclose(reg.height, 3.5)


def test_disjoint_spectral_subset(cubeviz_helper, spectral_cube_wcs):
    subset_plugin = SubsetPlugin(app=cubeviz_helper.app)
    data = Data(flux=np.ones((128, 128, 256)), label='Test Flux', coords=spectral_cube_wcs)
    cubeviz_helper.app.data_collection.append(data)

    cubeviz_helper.app.add_data_to_viewer('spectrum-viewer', 'Test Flux')
    cubeviz_helper.app.add_data_to_viewer('flux-viewer', 'Test Flux')

    spec_viewer = cubeviz_helper.app.get_viewer("spectrum-viewer")
    spec_viewer.apply_roi(XRangeROI(5, 15.5))

    # Add second region to Subset 1
    cubeviz_helper.app.session.edit_subset_mode.mode = OrMode
    spec_viewer.apply_roi(XRangeROI(30, 35))

    subsets = cubeviz_helper.app.get_subsets_from_viewer('spectrum-viewer')
    reg = subsets.get('Subset 1')

    assert len(reg) == 2
    assert isinstance(reg, SpectralRegion)
    assert_quantity_allclose(reg[0].lower, 5.0*u.Hz)
    assert_quantity_allclose(reg[0].upper, 15.0*u.Hz)
    assert_quantity_allclose(reg[1].lower, 30.0*u.Hz)
    assert_quantity_allclose(reg[1].upper, 35.0*u.Hz)

    assert subset_plugin.subset_selected == "Subset 1"
    assert subset_plugin.subset_types == [{"Subset type": "Range"}, {"Subset type": "Range"}]
    assert subset_plugin.subset_definitions[0]["Lower bound"] == 30
    assert subset_plugin.subset_definitions[0]["Upper bound"] == 35
    assert subset_plugin.subset_definitions[1]["Lower bound"] == 5
    assert subset_plugin.subset_definitions[1]["Upper bound"] == 15.5
