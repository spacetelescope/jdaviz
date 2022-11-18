import numpy as np
import pytest
from astropy import units as u
from astropy.tests.helper import assert_quantity_allclose
from glue.core import Data
from glue.core.roi import CircularROI, EllipticalROI, RectangularROI, XRangeROI
from glue.core.edit_subset_mode import OrMode
from numpy.testing import assert_allclose
from regions import EllipsePixelRegion, RectanglePixelRegion
from specutils import SpectralRegion

from jdaviz.core.marks import ShadowSpatialSpectral


def test_region_from_subset_2d(cubeviz_helper):
    data = Data(flux=np.ones((128, 128)), label='Test 2D Flux')
    cubeviz_helper.app.data_collection.append(data)

    subset_plugin = cubeviz_helper.app.get_tray_item_from_name('g-subset-plugin')

    cubeviz_helper.app.add_data_to_viewer('flux-viewer', 'Test 2D Flux')

    cubeviz_helper.app.get_viewer('flux-viewer').apply_roi(EllipticalROI(1, 3.5, 1.2, 3.3))

    subsets = cubeviz_helper.app.get_subsets_from_viewer('flux-viewer')
    reg = subsets.get('Subset 1')

    assert len(subsets) == 1
    assert isinstance(reg, EllipsePixelRegion)

    assert_allclose(reg.center.x, 1)
    assert_allclose(reg.center.y, 3.5)
    assert_allclose(reg.width, 2.4)
    assert_allclose(reg.height, 6.6)
    assert_allclose(reg.angle.value, 0)

    assert subset_plugin.subset_selected == "Subset 1"
    assert subset_plugin.subset_types == ["EllipticalROI"]
    assert subset_plugin.is_editable
    for key in ("orig", "value"):
        assert subset_plugin._get_value_from_subset_definition(0, "X Center", key) == 1
        assert subset_plugin._get_value_from_subset_definition(0, "Y Center", key) == 3.5
        assert subset_plugin._get_value_from_subset_definition(0, "X Radius", key) == 1.2
        assert subset_plugin._get_value_from_subset_definition(0, "Y Radius", key) == 3.3
        assert subset_plugin._get_value_from_subset_definition(0, "Angle", key) == 0

    # Recenter GUI should not be exposed, but API call would raise exception.
    with pytest.raises(NotImplementedError, match='Cannot recenter'):
        subset_plugin.vue_recenter_subset()


def test_region_from_subset_3d(cubeviz_helper):
    data = Data(flux=np.ones((128, 128, 256)), label='Test 3D Flux')
    cubeviz_helper.app.data_collection.append(data)

    subset_plugin = cubeviz_helper.app.get_tray_item_from_name('g-subset-plugin')
    assert subset_plugin.subset_selected == "Create New"

    cubeviz_helper.app.add_data_to_viewer('flux-viewer', 'Test 3D Flux')

    cubeviz_helper.app.get_viewer('flux-viewer').apply_roi(RectangularROI(1, 3.5, -0.2, 3.3))

    subsets = cubeviz_helper.app.get_subsets_from_viewer('flux-viewer')
    reg = subsets.get('Subset 1')

    assert len(subsets) == 1
    assert isinstance(reg, RectanglePixelRegion)

    assert_allclose(reg.center.x, 2.25)
    assert_allclose(reg.center.y, 1.55)
    assert_allclose(reg.width, 2.5)
    assert_allclose(reg.height, 3.5)
    assert_allclose(reg.angle.value, 0)

    assert subset_plugin.subset_selected == "Subset 1"
    assert subset_plugin.subset_types == ["RectangularROI"]
    assert subset_plugin.is_editable
    assert subset_plugin.get_center() == (2.25, 1.55)
    for key in ("orig", "value"):
        assert subset_plugin._get_value_from_subset_definition(0, "Xmin", key) == 1
        assert subset_plugin._get_value_from_subset_definition(0, "Xmax", key) == 3.5
        assert subset_plugin._get_value_from_subset_definition(0, "Ymin", key) == -0.2
        assert subset_plugin._get_value_from_subset_definition(0, "Ymax", key) == 3.3
        assert subset_plugin._get_value_from_subset_definition(0, "Angle", key) == 0

    # Mimic user changing something in Subset Tool GUI.
    subset_plugin._set_value_in_subset_definition(0, "Xmin", "value", 2)
    subset_plugin._set_value_in_subset_definition(0, "Ymin", "value", 0)
    subset_plugin._set_value_in_subset_definition(0, "Angle", "value", 45)  # ccw deg
    # "orig" is unchanged until user clicks Update button.
    assert subset_plugin._get_value_from_subset_definition(0, "Xmin", "orig") == 1
    assert subset_plugin._get_value_from_subset_definition(0, "Ymin", "orig") == -0.2
    assert subset_plugin._get_value_from_subset_definition(0, "Angle", "orig") == 0
    subset_plugin.vue_update_subset()
    for key in ("orig", "value"):
        assert subset_plugin._get_value_from_subset_definition(0, "Xmin", key) == 2
        assert subset_plugin._get_value_from_subset_definition(0, "Xmax", key) == 3.5
        assert subset_plugin._get_value_from_subset_definition(0, "Ymin", key) == 0
        assert subset_plugin._get_value_from_subset_definition(0, "Ymax", key) == 3.3
        assert subset_plugin._get_value_from_subset_definition(0, "Angle", key) == 45

    subsets = cubeviz_helper.app.get_subsets_from_viewer('flux-viewer')
    reg = subsets.get('Subset 1')

    assert_allclose(reg.center.x, 2.75)
    assert_allclose(reg.center.y, 1.65)
    assert_allclose(reg.width, 1.5)
    assert_allclose(reg.height, 3.3)
    assert_allclose(reg.angle.to_value(u.deg), 45)  # Might be stored in radians

    # Move the rectangle
    subset_plugin.set_center((3, 2), update=True)
    subsets = cubeviz_helper.app.get_subsets_from_viewer('flux-viewer')
    reg = subsets.get('Subset 1')
    assert_allclose(reg.center.x, 3)
    assert_allclose(reg.center.y, 2)
    assert_allclose(reg.width, 1.5)
    assert_allclose(reg.height, 3.3)
    assert_allclose(reg.angle.to_value(u.deg), 45)  # Might be stored in radians

    # Circular Subset
    flux_viewer = cubeviz_helper.app.get_viewer("flux-viewer")
    # We set the active tool here to trigger a reset of the Subset state to "Create New"
    flux_viewer.toolbar.active_tool = flux_viewer.toolbar.tools['bqplot:circle']
    cubeviz_helper.app.get_viewer('flux-viewer').apply_roi(CircularROI(xc=3, yc=4, radius=2.4))
    assert subset_plugin.subset_selected == "Subset 2"
    assert subset_plugin.subset_types == ["CircularROI"]
    assert subset_plugin.is_editable
    for key in ("orig", "value"):
        assert subset_plugin._get_value_from_subset_definition(0, "X Center", key) == 3
        assert subset_plugin._get_value_from_subset_definition(0, "Y Center", key) == 4
        assert subset_plugin._get_value_from_subset_definition(0, "Radius", key) == 2.4


def test_region_from_subset_profile(cubeviz_helper, spectral_cube_wcs):
    data = Data(flux=np.ones((128, 128, 256)), label='Test 1D Flux', coords=spectral_cube_wcs)
    subset_plugin = cubeviz_helper.app.get_tray_item_from_name('g-subset-plugin')

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
    assert subset_plugin.subset_types == ["Range"]
    assert subset_plugin.is_editable
    assert_allclose(subset_plugin.get_center(), 10.25)
    for key in ("orig", "value"):
        assert subset_plugin._get_value_from_subset_definition(0, "Lower bound", key) == 5
        assert subset_plugin._get_value_from_subset_definition(0, "Upper bound", key) == 15.5

    # Mimic user changing something in Subset Tool GUI.
    subset_plugin._set_value_in_subset_definition(0, "Lower bound", "value", 10)
    # "orig" is unchanged until user clicks Update button.
    assert subset_plugin._get_value_from_subset_definition(0, "Lower bound", "orig") == 5
    subset_plugin.vue_update_subset()
    for key in ("orig", "value"):
        assert subset_plugin._get_value_from_subset_definition(0, "Lower bound", key) == 10
        assert subset_plugin._get_value_from_subset_definition(0, "Upper bound", key) == 15.5

    subsets = cubeviz_helper.app.get_subsets_from_viewer('spectrum-viewer', subset_type='spectral')
    reg = subsets.get('Subset 1')

    assert_quantity_allclose(reg.lower, 10.0 * u.Hz)
    assert_quantity_allclose(reg.upper, 15.0 * u.Hz)

    # Move the Subset.
    subset_plugin.set_center(10, update=True)
    subsets = cubeviz_helper.app.get_subsets_from_viewer('spectrum-viewer', subset_type='spectral')
    reg = subsets.get('Subset 1')
    assert_quantity_allclose(reg.lower, 8 * u.Hz)
    assert_quantity_allclose(reg.upper, 12 * u.Hz)


def test_region_spectral_spatial(cubeviz_helper, spectral_cube_wcs):
    data = Data(flux=np.ones((128, 128, 256)), label='Test Flux', coords=spectral_cube_wcs)
    cubeviz_helper.app.data_collection.append(data)

    cubeviz_helper.app.add_data_to_viewer('spectrum-viewer', 'Test Flux')
    cubeviz_helper.app.add_data_to_viewer('flux-viewer', 'Test Flux')

    # use gaussian smooth plugin as a regression test for
    # https://github.com/spacetelescope/jdaviz/issues/1853
    cubeviz_helper.plugins['Gaussian Smooth'].smooth(add_data=True)

    spectrum_viewer = cubeviz_helper.app.get_viewer("spectrum-viewer")
    spectrum_viewer.apply_roi(XRangeROI(5, 15.5))

    # should be no spatial-spectral intersection marks yet
    assert len([m for m in spectrum_viewer.figure.marks if isinstance(m, ShadowSpatialSpectral)]) == 0  # noqa

    flux_viewer = cubeviz_helper.app.get_viewer("flux-viewer")
    # We set the active tool here to trigger a reset of the Subset state to "Create New"
    flux_viewer.toolbar.active_tool = flux_viewer.toolbar.tools['bqplot:rectangle']
    flux_viewer.apply_roi(RectangularROI(1, 3.5, -0.2, 3.3))

    assert len([m for m in spectrum_viewer.figure.marks if isinstance(m, ShadowSpatialSpectral)]) == 1  # noqa

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
    assert_allclose(reg.center.y, 1.55)
    assert_allclose(reg.width, 2.5)
    assert_allclose(reg.height, 3.5)

    # add another spectral subset to ensure the spatial-spectral intersection marks are created as
    # expected
    # reset the tool to force a new selection instead of the default "replace"
    spectrum_viewer.toolbar.active_tool = spectrum_viewer.toolbar.tools['jdaviz:panzoom']
    spectrum_viewer.toolbar.active_tool = spectrum_viewer.toolbar.tools['bqplot:xrange']
    spectrum_viewer.apply_roi(XRangeROI(3, 16))
    assert len([m for m in spectrum_viewer.figure.marks if isinstance(m, ShadowSpatialSpectral)]) == 2  # noqa


def test_disjoint_spectral_subset(cubeviz_helper, spectral_cube_wcs):
    subset_plugin = cubeviz_helper.app.get_tray_item_from_name('g-subset-plugin')
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
    assert subset_plugin.subset_types == ["Range", "Range"]
    assert not subset_plugin.is_editable
    assert subset_plugin.get_center() is None
    subset_plugin.set_center(99, update=True)   # This is no-op
    for key in ("orig", "value"):
        assert subset_plugin._get_value_from_subset_definition(0, "Lower bound", key) == 30
        assert subset_plugin._get_value_from_subset_definition(0, "Upper bound", key) == 35
        assert subset_plugin._get_value_from_subset_definition(1, "Lower bound", key) == 5
        assert subset_plugin._get_value_from_subset_definition(1, "Upper bound", key) == 15.5

    # This should not be possible via GUI but here we change
    # something to make sure no-op is really no-op.
    subset_plugin._set_value_in_subset_definition(0, "Lower bound", "value", 25)
    subset_plugin.vue_update_subset()
    # "value" here does not matter. It is going to get overwritten next time Subset is processed.
    assert subset_plugin._get_value_from_subset_definition(0, "Lower bound", "value") == 25
    assert subset_plugin._get_value_from_subset_definition(0, "Lower bound", "orig") == 30

    subsets = cubeviz_helper.app.get_subsets_from_viewer('spectrum-viewer')
    reg = subsets.get('Subset 1')
    assert_quantity_allclose(reg[1].lower, 30.0*u.Hz)  # Still the old value

    # See, never happened.
    subset_plugin.subset_selected = "Create New"
    subset_plugin.subset_selected = "Subset 1"
    assert subset_plugin._get_value_from_subset_definition(0, "Lower bound", "value") == 30
