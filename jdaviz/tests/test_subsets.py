import astropy.units as u
from astropy.tests.helper import assert_quantity_allclose
import numpy as np
import pytest
from glue.core import Data
from glue.core.roi import RectangularROI, XRangeROI
from glue.core.edit_subset_mode import OrMode
from numpy.testing import assert_allclose
from specutils import SpectralRegion
from regions import RectanglePixelRegion

from jdaviz.app import Application


@pytest.fixture
def jdaviz_app():
    return Application(configuration='cubeviz')


def test_region_from_subset_2d(jdaviz_app):
    data = Data(flux=np.ones((128, 128)), label='Test 2D Flux')
    jdaviz_app.data_collection.append(data)

    jdaviz_app.add_data_to_viewer('flux-viewer', 'Test 2D Flux')

    jdaviz_app.get_viewer('flux-viewer').apply_roi(RectangularROI(1, 3.5, -0.2, 3.3))

    subsets = jdaviz_app.get_subsets_from_viewer('flux-viewer')
    reg = subsets.get('Subset 1')

    assert len(subsets) == 1
    assert isinstance(reg, RectanglePixelRegion)

    assert_allclose(reg.center.x, 2.25)
    assert_allclose(reg.center.x, 2.25)
    assert_allclose(reg.center.y, 1.55)
    assert_allclose(reg.width, 2.5)
    assert_allclose(reg.height, 3.5)


def test_region_from_subset_3d(jdaviz_app):
    data = Data(flux=np.ones((256, 128, 128)), label='Test 3D Flux')
    jdaviz_app.data_collection.append(data)

    jdaviz_app.add_data_to_viewer('flux-viewer', 'Test 3D Flux')

    jdaviz_app.get_viewer('flux-viewer').apply_roi(RectangularROI(1, 3.5, -0.2, 3.3))

    subsets = jdaviz_app.get_subsets_from_viewer('flux-viewer')
    reg = subsets.get('Subset 1')

    assert len(subsets) == 1
    assert isinstance(reg, RectanglePixelRegion)

    assert_allclose(reg.center.x, 2.25)
    assert_allclose(reg.center.x, 2.25)
    assert_allclose(reg.center.y, 1.55)
    assert_allclose(reg.width, 2.5)
    assert_allclose(reg.height, 3.5)


def test_region_from_subset_profile(jdaviz_app, spectral_cube_wcs):
    data = Data(flux=np.ones((256, 128, 128)), label='Test 1D Flux', coords=spectral_cube_wcs)
    jdaviz_app.data_collection.append(data)

    jdaviz_app.add_data_to_viewer('spectrum-viewer', 'Test 1D Flux')

    jdaviz_app.get_viewer("spectrum-viewer").apply_roi(XRangeROI(5, 15.5))

    subsets = jdaviz_app.get_subsets_from_viewer('spectrum-viewer', subset_type='spectral')
    reg = subsets.get('Subset 1')

    assert len(subsets) == 1
    assert isinstance(reg, SpectralRegion)
    assert_quantity_allclose(reg.lower, 5.0 * u.Hz)
    assert_quantity_allclose(reg.upper, 15.0 * u.Hz)


def test_region_spectral_spatial(jdaviz_app, spectral_cube_wcs):
    data = Data(flux=np.ones((256, 128, 128)), label='Test Flux', coords=spectral_cube_wcs)
    jdaviz_app.data_collection.append(data)

    jdaviz_app.add_data_to_viewer('spectrum-viewer', 'Test Flux')
    jdaviz_app.add_data_to_viewer('flux-viewer', 'Test Flux')

    jdaviz_app.get_viewer("spectrum-viewer").apply_roi(XRangeROI(5, 15.5))

    flux_viewer = jdaviz_app.get_viewer("flux-viewer")
    # We set the active tool here to trigger a reset of the Subset state to "Create new"
    flux_viewer.toolbar.active_tool = flux_viewer.toolbar.tools['bqplot:rectangle']
    flux_viewer.apply_roi(RectangularROI(1, 3.5, -0.2, 3.3))

    subsets = jdaviz_app.get_subsets_from_viewer('spectrum-viewer', subset_type='spectral')
    reg = subsets.get('Subset 1')

    assert len(subsets) == 1
    assert isinstance(reg, SpectralRegion)

    assert_quantity_allclose(reg.lower, 5.0 * u.Hz)
    assert_quantity_allclose(reg.upper, 15 * u.Hz)

    subsets = jdaviz_app.get_subsets_from_viewer('flux-viewer', subset_type='spatial')
    reg = subsets.get('Subset 2')

    assert len(subsets) == 1
    assert isinstance(reg, RectanglePixelRegion)
    assert_allclose(reg.center.x, 2.25)
    assert_allclose(reg.center.x, 2.25)
    assert_allclose(reg.center.y, 1.55)
    assert_allclose(reg.width, 2.5)
    assert_allclose(reg.height, 3.5)


def test_disjoint_spectral_subset(jdaviz_app, spectral_cube_wcs):
    data = Data(flux=np.ones((256, 128, 128)), label='Test Flux', coords=spectral_cube_wcs)
    jdaviz_app.data_collection.append(data)

    jdaviz_app.add_data_to_viewer('spectrum-viewer', 'Test Flux')
    jdaviz_app.add_data_to_viewer('flux-viewer', 'Test Flux')

    spec_viewer = jdaviz_app.get_viewer("spectrum-viewer")
    spec_viewer.apply_roi(XRangeROI(5, 15.5))

    # Add second region to Subset 1
    jdaviz_app.session.edit_subset_mode.mode = OrMode
    spec_viewer.apply_roi(XRangeROI(30, 35))

    subsets = jdaviz_app.get_subsets_from_viewer('spectrum-viewer')
    reg = subsets.get('Subset 1')

    assert len(reg) == 2
    assert isinstance(reg, SpectralRegion)
    assert_quantity_allclose(reg[0].lower, 5.0*u.Hz)
    assert_quantity_allclose(reg[0].upper, 15.0*u.Hz)
    assert_quantity_allclose(reg[1].lower, 30.0*u.Hz)
    assert_quantity_allclose(reg[1].upper, 35.0*u.Hz)
