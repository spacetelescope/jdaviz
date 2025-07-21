import pytest
import numpy as np
import astropy.units as u
from specutils import SpectralRegion


def test_spectralsubsetselect(specviz_helper, spectrum1d):
    # apply mask to spectrum to check selected subset is masked:
    mask = spectrum1d.flux < spectrum1d.flux.mean()
    spectrum1d.mask = mask

    specviz_helper.load_data(spectrum1d)
    sv = specviz_helper.app.get_viewer('spectrum-viewer')
    # create a "Subset 1" entry
    subset_plugin = specviz_helper.plugins['Subset Tools']
    subset_plugin.import_region(SpectralRegion(6500 * spectrum1d.spectral_axis.unit,
                                               7400 * spectrum1d.spectral_axis.unit))

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
        (spectrum1d.wavelength.to_value(u.AA) < 6500) |
        (spectrum1d.wavelength.to_value(u.AA) > 7400)
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


@pytest.mark.filterwarnings('ignore:No observer defined on WCS')
def test_viewer_select(cubeviz_helper, spectrum1d_cube):
    app = cubeviz_helper.app
    cubeviz_helper.load_data(spectrum1d_cube, data_label='test')
    fv = app.get_viewer("flux-viewer")
    sv = app.get_viewer('spectrum-viewer')

    # export plugin uses the mixin
    p = cubeviz_helper.plugins['Export']
    # 2 viewers available (no uncertainty cube loaded)
    assert len(p.viewer.ids) == 2
    assert len(p.viewer.references) == 2
    assert len(p.viewer.labels) == 2
    assert p.viewer.selected_obj == fv

    # set by reference
    p.viewer = 'spectrum-viewer'
    assert p.viewer.selected_obj == sv

    # try setting based on id instead of reference
    p.viewer = p.viewer.ids[0]
    assert p.viewer.selected == p.viewer.labels[0]


class TestSetupRelevance:
    fake_traitlet = 'fake_traitlet1'

    def fake_set_relevant(self, *args):
        self.bad_return = 'useless return'
        return 'useless return'

    @pytest.mark.parametrize(
        ('irrelevant_msg', 'result_msg'), [
            ('', f'No {fake_traitlet} available'),
            ('irrelevant message', 'irrelevant message')
        ])
    def test_setup_relevance_with_fake_traitlets(self,
                                                 deconfigged_plugin, irrelevant_msg, result_msg):
        # Starting with at least one fake traitlet to make sure the irrelevant message
        # is set correctly when it can't find the attribute
        real_traitlets = [traitlet for traitlet in dir(deconfigged_plugin)
                          if getattr(deconfigged_plugin, traitlet, None)]
        traitlets = real_traitlets + [self.fake_traitlet]

        deconfigged_plugin._obj.setup_relevance(non_empty_traitlets=traitlets,
                                                irrelevant_msg=irrelevant_msg)

        assert deconfigged_plugin._obj._non_empty_traitlets == traitlets
        assert deconfigged_plugin._obj._custom_irrelevant_msg == irrelevant_msg
        assert deconfigged_plugin._obj.irrelevant_msg == result_msg
        assert deconfigged_plugin._obj._set_relevant() is None

        # Now using our own set_relevant function
        deconfigged_plugin._obj.setup_relevance(non_empty_traitlets=traitlets,
                                                irrelevant_msg=irrelevant_msg,
                                                set_relevant=self.fake_set_relevant)

        assert deconfigged_plugin._obj._non_empty_traitlets == traitlets
        assert deconfigged_plugin._obj._custom_irrelevant_msg == irrelevant_msg
        assert deconfigged_plugin._obj._set_relevant() is None

        # Set existing (real) traitlet to trigger observe
        # and check that our custom function indeed runs.
        for traitlet in real_traitlets:
            self.bad_return = 'useful return?'
            try:
                setattr(deconfigged_plugin, traitlet, 'fake update')
            # Some traitlets are callable/can't be set by this specific string
            except (ValueError, AttributeError):
                continue
            else:
                assert self.bad_return == self.fake_set_relevant()

    # Using all real traitlets now and the default/existing set_relevant()
    def test_setup_relevance_with_real_traitlets(self, deconfigged_plugin):
        traitlets = [traitlet for traitlet in dir(deconfigged_plugin)
                     if getattr(deconfigged_plugin, traitlet, None)]

        deconfigged_plugin._obj.setup_relevance(non_empty_traitlets=traitlets)

        assert deconfigged_plugin._obj._non_empty_traitlets == traitlets
        assert deconfigged_plugin._obj._custom_irrelevant_msg == ''
        assert deconfigged_plugin._obj.irrelevant_msg == ''
        assert deconfigged_plugin._obj._set_relevant() is None

        # Check that the traitlets are being observed
        # by checking if irrelevant message is reset correctly
        for traitlet in traitlets:
            deconfigged_plugin._obj.irrelevant_msg = 'fake irrelevant message'
            try:
                setattr(deconfigged_plugin, traitlet, 'fake update')
            # Some traitlets are callable/can't be set by this specific string
            except (ValueError, AttributeError):
                continue
            else:
                assert deconfigged_plugin._obj.irrelevant_msg == ''
