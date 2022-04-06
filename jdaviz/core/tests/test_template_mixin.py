import pytest

from glue.core.roi import XRangeROI


def test_spectralsubsetselect(specviz_helper, spectrum1d):
    specviz_helper.load_spectrum(spectrum1d)
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
    assert p.spectral_subset.selected_min_max(spectrum1d) == (expected_min, expected_max)

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
    assert len(p.viewer.ids) == 4
    assert len(p.viewer.references) == 4
    assert len(p.viewer.labels) == 4
    assert p.viewer.selected_obj == fv

    # set by reference
    p.viewer_selected = 'spectrum-viewer'
    assert p.viewer.selected_obj == sv

    # try setting based on id instead of reference
    p.viewer_selected = p.viewer.ids[0]
    assert p.viewer_selected == p.viewer.labels[0]
