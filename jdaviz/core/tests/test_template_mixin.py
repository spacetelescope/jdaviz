import pytest
import numpy as np
import astropy.units as u
from specutils import SpectralRegion
from traitlets import Any, Instance


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

    set_relevant_msg = 'stale message'
    new_set_relevant_msg = 'fresh message'
    sad_msg = "I don't want to be made irrelevant"

    def fake_set_relevant(self, *args):
        self.set_relevant_msg = self.new_set_relevant_msg
        return self.new_set_relevant_msg

    @staticmethod
    def setup_traitlets(plugin_obj):
        return [trait_name for trait_name in plugin_obj.traits()
                if getattr(plugin_obj, trait_name, False)]

    # NOTE: deconfigged_plugin *is* a custom parametrization (see conftest.py)
    # so these will run with all the plugins available at initialization.
    def test_setup_relevance_with_real_traitlets(self, deconfigged_plugin):
        deconfigged_plugin_obj = deconfigged_plugin._obj
        traitlets = self.setup_traitlets(deconfigged_plugin_obj)

        # Testing basic functionality
        deconfigged_plugin_obj.setup_relevance(non_empty_traitlets=traitlets)

        assert deconfigged_plugin_obj._non_empty_traitlets == traitlets
        assert deconfigged_plugin_obj._custom_irrelevant_msg == ''
        # Everything is real and _set_relevant() worked for all,
        # i.e. irrelevant_msg is an empty string
        assert deconfigged_plugin_obj.irrelevant_msg == ''

        # Now to check that the traitlets are observed as expected
        # and that _set_relevant() therefore runs as expected
        observed_traitlets = deconfigged_plugin_obj._trait_notifiers
        # 'Observed' as expected
        assert set(traitlets).issubset(set(observed_traitlets.keys()))

        # Keep trait_name around for future debugging if necessary
        observed_traitlet_methods = {trait_name: observed_traitlets[trait_name]['change']
                                     for trait_name in traitlets}

        # Check to see if fake_set_relevant is available and runs
        # when accessing the observed quantity
        for _, observe_methods in observed_traitlet_methods.items():
            deconfigged_plugin_obj.irrelevant_msg = self.sad_msg

            # traits may be observed by more than one method
            # traitlet ObserverHandlers don't have __name__ so we use getattr
            all_results = [method() for method in observe_methods
                           if getattr(method, '__name__', None) == '_set_relevant']

            # _set_relevant() runs as expected
            assert deconfigged_plugin_obj.irrelevant_msg == ''
            # And double check that the function output what we expect (Nones in this case)
            assert deconfigged_plugin_obj._set_relevant() in all_results

    # The 'observes' stack otherwise this could be combined with the above test
    # Alternatively, a custom function could be used (but that's [currently] a separate test!)
    @pytest.mark.parametrize(
        ('irrelevant_msg', 'result_msg'), [
            ('', f'No fake_traitlet available'),
            ('irrelevant message', 'irrelevant message')
        ])
    def test_setup_relevance_with_fake_traitlets(self,
                                                 deconfigged_plugin, irrelevant_msg, result_msg):
        # Starting with at least one fake traitlet to make sure the irrelevant message
        # is set correctly when it can't find the attribute
        deconfigged_plugin_obj = deconfigged_plugin._obj
        traitlets = self.setup_traitlets(deconfigged_plugin_obj) + ['fake_traitlet']

        deconfigged_plugin_obj.setup_relevance(non_empty_traitlets=traitlets,
                                               irrelevant_msg=irrelevant_msg)

        # Check that the fake traitlet is the only thing that triggers the irrelevant message
        assert deconfigged_plugin_obj._non_empty_traitlets == traitlets
        assert deconfigged_plugin_obj._custom_irrelevant_msg == irrelevant_msg
        assert deconfigged_plugin_obj.irrelevant_msg == result_msg

        # Following the same prescription as test..._with_real_traitlets...
        observed_traitlets = deconfigged_plugin_obj._trait_notifiers
        assert set(traitlets).issubset(set(observed_traitlets.keys()))

        observed_traitlet_methods = {trait_name: observed_traitlets[trait_name]['change']
                                     for trait_name in traitlets}

        for _, observe_methods in observed_traitlet_methods.items():
            deconfigged_plugin_obj.irrelevant_msg = self.sad_msg

            all_results = [method() for method in observe_methods
                           if getattr(method, '__name__', None) == '_set_relevant']

            # Check that irrelevant_msg is indeed rewritten and
            # due to the ordering of the list should be our result_msg
            assert deconfigged_plugin_obj.irrelevant_msg == result_msg
            assert deconfigged_plugin_obj._set_relevant() in all_results

    def test_setup_relevance_with_custom_function(self, deconfigged_plugin):

        deconfigged_plugin_obj = deconfigged_plugin._obj
        traitlets = self.setup_traitlets(deconfigged_plugin_obj)

        # Now using our own set_relevant function
        deconfigged_plugin_obj.setup_relevance(non_empty_traitlets=traitlets,
                                               set_relevant=self.fake_set_relevant)

        assert deconfigged_plugin_obj._non_empty_traitlets == traitlets
        assert deconfigged_plugin_obj._custom_irrelevant_msg == ''
        # NOTE: deconfigged_plugin_obj.irrelevant_msg is not being set by this test
        # since we're using a custom function

        # Check that the default _set_relevant() still exists and
        # isn't somehow miraculously overwritten
        assert deconfigged_plugin_obj._set_relevant() is None
        assert self.set_relevant_msg == self.new_set_relevant_msg

        # Again, same as test...with_real/fake_traitlets
        observed_traitlets = deconfigged_plugin_obj._trait_notifiers
        assert set(traitlets).issubset(set(observed_traitlets.keys()))

        observed_traitlet_methods = {trait_name: observed_traitlets[trait_name]['change']
                                     for trait_name in traitlets}

        for _, observe_methods in observed_traitlet_methods.items():
            not_fresh_msg = 'less stale message but still not great'
            self.set_relevant_msg = not_fresh_msg

            all_results = [method() for method in observe_methods
                           if getattr(method, '__name__', None) == 'fake_set_relevant']

            # Check that self.set_relevant_msg is overwritten by our fake_set_relevant
            assert self.set_relevant_msg in all_results
            # Double check that it is indeed new_set_relevant_msg
            assert self.new_set_relevant_msg in all_results
            assert self.fake_set_relevant() in all_results
