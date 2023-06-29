import pytest
import numpy as np
import astropy.units as u

from glue.core.roi import XRangeROI, CircularROI
from specutils import Spectrum1D


def test_spectralsubsetselect(specviz_helper, spectrum1d):
    # apply mask to spectrum to check selected subset is masked:
    mask = spectrum1d.flux < spectrum1d.flux.mean()
    spectrum1d.mask = mask

    specviz_helper.load_data(spectrum1d)
    sv = specviz_helper.app.get_viewer('spectrum-viewer')
    # create a "Subset 1" entry
    sv.apply_roi(XRangeROI(6500, 7400))

    # model fitting uses the mixin
    p = specviz_helper.app.get_tray_item_from_name('g-model-fitting')
    assert len(p.spectral_subset.labels) == 2  # Entire Spectrum, Subset 1
    assert len(p.spectral_subset_items) == 2
    assert p.spectral_subset_selected == 'Entire Spectrum'
    assert p.spectral_subset_selected_has_subregions is False
    assert p.spectral_subset.selected_obj is None
    p.spectral_subset_selected = 'Subset 1'
    assert p.spectral_subset_selected_has_subregions is False
    assert p.spectral_subset.selected_obj is not None
    expected_min = spectrum1d.spectral_axis[spectrum1d.spectral_axis.value >= 6500][0]
    expected_max = spectrum1d.spectral_axis[spectrum1d.spectral_axis.value <= 7400][-1]
    np.testing.assert_allclose(expected_min.value, 6666.66666667, atol=1e-5)
    np.testing.assert_allclose(expected_max.value, 7333.33333333, atol=1e-5)
    assert p.spectral_subset.selected_min_max(spectrum1d) == (6500 * u.AA, 7400 * u.AA)

    # check selected subset mask available via API:
    expected_mask_with_spectral_subset = (
        (spectrum1d.wavelength.to(u.AA).value < 6500) |
        (spectrum1d.wavelength.to(u.AA).value > 7400)
    )
    assert np.all(
        expected_mask_with_spectral_subset == p.spectral_subset.selected_subset_mask
    )

    assert p.spectral_subset.app == p.app
    assert p.spectral_subset.spectrum_viewer == sv

    # line analysis uses custom components, one of which is still named spectral_subset
    p = specviz_helper.app.get_tray_item_from_name('specviz-line-analysis')
    assert len(p.spectral_subset.labels) == 2  # Entire Spectrum, Subset 1
    assert len(p.spectral_subset_items) == 2
    assert p.spectral_subset_selected == 'Entire Spectrum'
    assert p.spectral_subset.selected_obj is None
    p.spectral_subset_selected = 'Subset 1'
    assert p.spectral_subset.selected_obj is not None


def test_spatialsubsetselect(cubeviz_helper, spectrum1d_cube):
    cubeviz_helper.load_data(spectrum1d_cube)
    fv = cubeviz_helper.app.get_viewer('flux-viewer')
    # create a "Subset 1" entry in spatial dimension
    fv.apply_roi(CircularROI(0.5, 0.5, 1))

    # model fitting uses the mixin
    p = cubeviz_helper.app.get_tray_item_from_name('g-model-fitting')
    assert len(p.spatial_subset.labels) == 2  # Entire Cube, Subset 1
    assert len(p.spatial_subset_items) == 2
    assert p.spatial_subset_selected == 'Entire Cube'
    assert p.spatial_subset.selected_obj is None
    p.spatial_subset_selected = 'Subset 1'
    assert p.spatial_subset.selected_obj is not None

    # put selected subset mask in same shape as expected mask, check it is preserved
    selected_mask = np.swapaxes(p.spatial_subset.selected_subset_mask, 1, 0)

    expected_mask = np.ones_like(spectrum1d_cube.flux.value).astype(bool)
    expected_mask[:2, :2, :] = False

    assert np.all(selected_mask == expected_mask)


def test_spectral_subsetselect_collapsed(cubeviz_helper, spectrum1d_cube):
    cubeviz_helper.load_data(spectrum1d_cube)
    sv = cubeviz_helper.app.get_viewer('spectrum-viewer')
    # create a "Subset 1" entry
    sv.apply_roi(XRangeROI(6500, 7400))

    # model fitting uses the mixin
    p = cubeviz_helper.app.get_tray_item_from_name('g-model-fitting')

    # Should work when dimensions of mask match the flux:
    spectrum1d_cube.mask = np.zeros_like(spectrum1d_cube.flux.value).astype(bool)
    p._apply_subset_masks(spectrum1d_cube, p.spatial_subset)
    assert spectrum1d_cube.mask.shape == spectrum1d_cube.flux.shape

    # and when dimensions of mask match a collapsed spectrum:
    data = cubeviz_helper.app.data_collection[0]
    collapsed_spectrum = data.get_object(cls=Spectrum1D)

    collapsed_spectrum.mask = np.zeros_like(collapsed_spectrum.spectral_axis.value).astype(bool)
    p._apply_subset_masks(collapsed_spectrum, p.spectral_subset)
    assert collapsed_spectrum.mask.shape == collapsed_spectrum.spectral_axis.shape


@pytest.mark.filterwarnings('ignore:No observer defined on WCS')
def test_viewer_select(cubeviz_helper, spectrum1d_cube):
    app = cubeviz_helper.app
    app.add_data(spectrum1d_cube, 'test')
    app.add_data_to_viewer("spectrum-viewer", "test")
    app.add_data_to_viewer("flux-viewer", "test")
    fv = app.get_viewer("flux-viewer")
    sv = app.get_viewer("spectrum-viewer")

    # export plot uses the mixin
    p = app.get_tray_item_from_name('g-export-plot')
    assert len(p.viewer.ids) == 3
    assert len(p.viewer.references) == 3
    assert len(p.viewer.labels) == 3
    assert p.viewer.selected_obj == fv

    # set by reference
    p.viewer_selected = 'spectrum-viewer'
    assert p.viewer.selected_obj == sv

    # try setting based on id instead of reference
    p.viewer_selected = p.viewer.ids[0]
    assert p.viewer_selected == p.viewer.labels[0]
