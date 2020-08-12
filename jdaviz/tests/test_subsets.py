import numpy as np
import pytest
from glue.core import Data
from glue.core.roi import RectangularROI, XRangeROI
from glue.core.subset import RoiSubsetState
from numpy.testing import assert_allclose
from regions import RectanglePixelRegion

from jdaviz.app import Application


@pytest.fixture
def jdaviz_app():
    return Application(configuration='cubeviz')


def test_region_from_subset_2d(jdaviz_app):
    data = Data(flux=np.ones((128, 128)), label='Test 2D Flux')
    jdaviz_app.data_collection.append(data)

    subset_state = RoiSubsetState(data.pixel_component_ids[1],
                                  data.pixel_component_ids[0],
                                  RectangularROI(1, 3.5, -0.2, 3.3))

    jdaviz_app.add_data_to_viewer('flux-viewer', 'Test 2D Flux')

    jdaviz_app.data_collection.new_subset_group(
        subset_state=subset_state, label='rectangular')

    subsets = jdaviz_app.get_subsets_from_viewer('flux-viewer')
    reg = subsets.get('rectangular')

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

    subset_state = RoiSubsetState(data.pixel_component_ids[1],
                                  data.pixel_component_ids[0],
                                  RectangularROI(1, 3.5, -0.2, 3.3))

    jdaviz_app.add_data_to_viewer('flux-viewer', 'Test 3D Flux')

    jdaviz_app.data_collection.new_subset_group(
        subset_state=subset_state, label='rectangular')

    subsets = jdaviz_app.get_subsets_from_viewer('flux-viewer')
    reg = subsets.get('rectangular')

    assert len(subsets) == 1
    assert isinstance(reg, RectanglePixelRegion)

    assert_allclose(reg.center.x, 2.25)
    assert_allclose(reg.center.x, 2.25)
    assert_allclose(reg.center.y, 1.55)
    assert_allclose(reg.width, 2.5)
    assert_allclose(reg.height, 3.5)


def test_region_from_subset_profile(jdaviz_app):
    data = Data(flux=np.ones((256, 128, 128)), label='Test 1D Flux')
    jdaviz_app.data_collection.append(data)

    subset_state = RoiSubsetState(data.pixel_component_ids[1],
                                  data.pixel_component_ids[0],
                                  XRangeROI(1, 3.5))

    jdaviz_app.add_data_to_viewer('spectrum-viewer', 'Test 1D Flux')

    jdaviz_app.data_collection.new_subset_group(
        subset_state=subset_state, label='rectangular')

    subsets = jdaviz_app.get_subsets_from_viewer('spectrum-viewer')
    reg = subsets.get('rectangular')

    assert len(subsets) == 1
    assert isinstance(reg, RectanglePixelRegion)

    assert_allclose(reg.center.x, 2.25)
    assert_allclose(reg.center.y, 128)
    assert_allclose(reg.width, 2.5)
    assert_allclose(reg.height, 256)
