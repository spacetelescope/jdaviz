import io
import os
import re
import pytest
import numpy as np
import astropy.units as u
from astropy.table import Table
from specutils import SpectralRegion

from jdaviz.core.template_mixin import TableMixin


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


class TestObserveTraitletsForRelevancy:

    fake_traitlets = ['fake_traitlet1', 'fake_traitlet2']

    set_relevant_msg = 'stale message'
    new_set_relevant_msg = 'fresh message'
    sad_msg = "I don't want to be made irrelevant :("

    def if_fake_truthy(self, *args):
        self.set_relevant_msg = self.new_set_relevant_msg

    def setup_plugin_obj_and_traitlets(self, config_helper):
        plugins = config_helper.plugins

        plugin_obj = plugins['Test Fake Plugin']._obj

        self.if_all_truthy = plugin_obj.relevant_if_all_truthy
        self.if_any_truthy = plugin_obj.relevant_if_any_truthy

        return plugin_obj, [trait_name for trait_name in plugin_obj.traits()
                            if getattr(plugin_obj, trait_name, False)]

    def test_setup_relevant_if_truthy(self, deconfigged_helper):
        deconfigged_plugin_obj, traitlets = self.setup_plugin_obj_and_traitlets(
            deconfigged_helper)

        default_irrelevant_msg = (f"At least one of or all of {', '.join(traitlets)} "
                                  f"are not available")

        # Covers no _traitlets_to_observe set
        with pytest.raises(AttributeError,
                           match=re.escape('_traitlets_to_observe has not been '
                                           'set yet (by `observe_traitlets_for_relevancy`).')):
            deconfigged_plugin_obj._setup_relevant_if_truthy(None)

        # Covers _traitlets_to_observe set and default message
        deconfigged_plugin_obj._traitlets_to_observe = traitlets
        traitlets_from_setup, truthy_traitlets, irrelevant_msg = (
            deconfigged_plugin_obj._setup_relevant_if_truthy(None))
        assert traitlets_from_setup == traitlets
        assert truthy_traitlets == traitlets
        assert irrelevant_msg == default_irrelevant_msg

        # Covers traitlets passed in as arg and default message
        traitlets_from_setup, truthy_traitlets, irrelevant_msg = (
            deconfigged_plugin_obj._setup_relevant_if_truthy(traitlets))
        assert traitlets_from_setup == traitlets
        assert truthy_traitlets == traitlets
        assert irrelevant_msg == default_irrelevant_msg

    @pytest.mark.parametrize('method_type', ['all', 'any'])
    def test_relevant_if_truthy(self, deconfigged_helper, method_type):
        deconfigged_plugin_obj, traitlets = self.setup_plugin_obj_and_traitlets(
            deconfigged_helper)

        method = getattr(self, f'if_{method_type}_truthy')

        # Checking the default argument (None) when nothing is observed yet
        with pytest.raises(AttributeError,
                           match=re.escape('_traitlets_to_observe has not been set yet '
                                           '(by `observe_traitlets_for_relevancy`).')):
            method()

        # Check that irrelevant message is set correctly for relevant traitlets
        result = method(traitlets)
        assert result == ''

        # Check that irrelevant message is set correctly for solely irrelevant traitlets
        result = method(self.fake_traitlets)
        assert result == (f"At least one of or all of {', '.join(self.fake_traitlets)} "
                          f"are not available")

        # Check that irrelevant message is set correctly for relevant + irrelevant traitlets
        traitlets += self.fake_traitlets
        result_default_msg = method(traitlets)

        # Check that irrelevant message is set correctly for relevant + irrelevant traitlets
        if method_type == 'all':
            assert result_default_msg == (f"At least one of or all of {', '.join(traitlets)} "
                                          f"are not available")
        elif method_type == 'any':
            assert result_default_msg == ''

    @pytest.mark.parametrize('method_type', ['all', 'any', 'fake'])
    def test_default_set_relevant(self, deconfigged_helper, method_type):
        deconfigged_plugin_obj, traitlets = self.setup_plugin_obj_and_traitlets(deconfigged_helper)
        deconfigged_plugin_obj._irrelevant_msg_callback = getattr(self, f'if_{method_type}_truthy')
        deconfigged_plugin_obj._traitlets_to_observe = traitlets

        # Real traitlets
        deconfigged_plugin_obj._set_relevant()
        if deconfigged_plugin_obj.irrelevant_msg is None:
            # i.e. when the fake method is used
            assert self.set_relevant_msg == self.new_set_relevant_msg
            self.set_relevant_msg = 'newly staled'
        else:
            assert deconfigged_plugin_obj.irrelevant_msg == ''

        # Real + Fake Traitlets
        # Thanks to mutability we shouldn't also have to update '_traitlets_to_observe'
        traitlets += self.fake_traitlets
        deconfigged_plugin_obj._set_relevant()
        if deconfigged_plugin_obj.irrelevant_msg is None:
            # i.e. when the fake method is used
            assert self.set_relevant_msg == self.new_set_relevant_msg
            self.set_relevant_msg = 'newly staled'

        else:
            if method_type == 'all':
                assert deconfigged_plugin_obj.irrelevant_msg == (f"At least one of or all of "
                                                                 f"{', '.join(traitlets)} "
                                                                 f"are not available")
            elif method_type == 'any':
                assert deconfigged_plugin_obj.irrelevant_msg == ''

    @pytest.mark.parametrize('additional_traitlets', [[], fake_traitlets])
    def test_observe_traitlets_for_relevancy(self,
                                             deconfigged_helper, additional_traitlets):
        deconfigged_plugin_obj, traitlets = self.setup_plugin_obj_and_traitlets(deconfigged_helper)
        traitlets += additional_traitlets

        if len(additional_traitlets) == 0:
            # i.e. irrelevant_msg is an empty string
            expected_msg = ''
        else:
            # Real + fake so the default (if_all_truthy) is the observer
            expected_msg = f"At least one of or all of {', '.join(traitlets)} are not available"

        # Testing default functionality
        deconfigged_plugin_obj.observe_traitlets_for_relevancy(traitlets)
        assert deconfigged_plugin_obj._traitlets_to_observe == traitlets
        assert (deconfigged_plugin_obj._irrelevant_msg_callback() ==
                deconfigged_plugin_obj.relevant_if_all_truthy())

        assert deconfigged_plugin_obj.irrelevant_msg == expected_msg

        # Now to check that the traitlets are observed as expected
        # and that _set_relevant() therefore runs as expected
        observed_traitlets = deconfigged_plugin_obj._trait_notifiers
        # 'Observed' as expected
        assert set(traitlets).issubset(set(observed_traitlets.keys()))

        # Keep trait_name around for future debugging if necessary
        observed_traitlet_methods = {trait_name: observed_traitlets[trait_name]['change']
                                     for trait_name in traitlets}

        # Check to see if _set_relevant is available and runs
        # when accessing the observed quantity
        for _, observe_methods in observed_traitlet_methods.items():
            deconfigged_plugin_obj.irrelevant_msg = self.sad_msg

            # Run the method to update irrelevant_msg
            # traits may be observed by more than one method
            # traitlet ObserverHandlers don't have __name__ so we use getattr
            all_results = [method() for method in observe_methods
                           if getattr(method, '__name__', None) == '_set_relevant']

            # _set_relevant() ran as expected
            assert deconfigged_plugin_obj.irrelevant_msg == expected_msg
            # And double check that the function output what we expect (Nones in this case)
            assert deconfigged_plugin_obj._set_relevant() in all_results

    @pytest.mark.parametrize('additional_traitlets', [[], fake_traitlets])
    def test_observe_traitlets_for_relevancy_with_fake_callback(
            self, deconfigged_helper, additional_traitlets):
        deconfigged_plugin_obj, traitlets = self.setup_plugin_obj_and_traitlets(
            deconfigged_helper)
        traitlets += additional_traitlets

        deconfigged_plugin_obj.observe_traitlets_for_relevancy(
            traitlets, irrelevant_msg_callback=self.if_fake_truthy)
        assert deconfigged_plugin_obj._traitlets_to_observe == traitlets
        assert (deconfigged_plugin_obj._irrelevant_msg_callback() ==
                self.if_fake_truthy())

        # Checking that _set_relevant ran and resetting the message
        assert self.set_relevant_msg == self.new_set_relevant_msg

        # Now to check that the traitlets are observed as expected
        # and that _set_relevant() therefore runs as expected
        observed_traitlets = deconfigged_plugin_obj._trait_notifiers
        # 'Observed' as expected
        assert set(traitlets).issubset(set(observed_traitlets.keys()))

        # Keep trait_name around for future debugging if necessary
        observed_traitlet_methods = {trait_name: observed_traitlets[trait_name]['change']
                                     for trait_name in traitlets}

        # Check to see if _set_relevant is available and runs
        # when accessing the observed quantity
        for _, observe_methods in observed_traitlet_methods.items():
            not_fresh_msg = 'less stale message but still not great'
            self.set_relevant_msg = not_fresh_msg

            # Run the method to update irrelevant_msg
            # traits may be observed by more than one method
            # traitlet ObserverHandlers don't have __name__ so we use getattr
            _ = [method() for method in observe_methods
                 if getattr(method, '__name__', None) == '_set_relevant']

            # Check that self.set_relevant_msg is overwritten by our if_fake_truthy
            # behind the scenes
            assert self.set_relevant_msg != not_fresh_msg


def test_select_plugin_component_map_value(imviz_helper, multi_extension_image_hdu_wcs):
    ldr = imviz_helper.loaders['object']
    ldr.object = multi_extension_image_hdu_wcs
    selection_obj = ldr.importer.extension

    # Check default selection
    assert selection_obj.selected == [selection_obj.choices[0]]

    # Check set selected directly via wildcard
    selection_obj.selected = '*'
    assert selection_obj.selected == selection_obj.choices
    choices_before = selection_obj.choices

    # Check set selected directly via ? wildcard
    selection_obj.selected = '*MASK,?]'
    assert selection_obj.selected == [selection_obj.choices[1]]
    choices_before = selection_obj.choices

    selection_obj.fake_attribute = 'item1'
    # Check that a different attribute *does not* trigger the wildcard logic
    # i.e. it gets set as-is and doesn't go through `choices`
    selection_obj.fake_attribute = ['fake * item1', 'fake item2']
    assert selection_obj.fake_attribute == ['fake * item1', 'fake item2']
    assert selection_obj.choices == choices_before


class FakeTable(TableMixin):
    template = ''

    def __init__(self, session, catalog, *args, **kwargs):
        self.session = session
        self._plugin_name = 'test-fake-table'
        super().__init__(*args, **kwargs)
        self.table._qtable = catalog


def astropy_table_write_formats():
    table_obj = Table({'a': [1, 2], 'b': [3, 4]})
    buf = io.StringIO()
    table_obj.write.list_formats(out=buf)
    output = buf.getvalue()

    # Output looks like this:
    #            Format           Read Write Auto-identify Deprecated
    # --------------------------- ---- ----- ------------- ----------
    #                       ascii  Yes   Yes            No
    #                ascii.aastex  Yes   Yes            No
    #                 ascii.basic  Yes   Yes            No

    valid_formats = []
    for line in output.splitlines():
        if line.strip().startswith('Format') or line.strip().startswith('--------'):
            continue

        split_line = line.strip().split()
        if len(split_line) == 5 and split_line[-1] == 'Yes':
            # Deprecated
            continue
        valid_formats.append(line.strip().split()[0])

    return valid_formats


def test_export_table_special_cases():
    valid_formats = astropy_table_write_formats()

    # These are special cases for formats that are currently supported by astropy but require
    # some specific details to be handled. If these get removed in the future, then
    # we can remove the special handling in `export_table`.
    assert {'asdf',
            'hdf5',
            'ascii.tdat',
            'votable',
            'parquet',
            'parquet.votable',
            'votable.parquet',
            'ascii.ipac'}.issubset(set(valid_formats))


@pytest.mark.parametrize('valid_format', astropy_table_write_formats())
def test_export_table(deconfigged_helper, source_catalog, tmp_path, valid_format):
    table_obj = FakeTable(deconfigged_helper.app.session, source_catalog)

    tmp_filename = tmp_path / 'temp_table'
    filename = f"{tmp_filename}_{valid_format}"

    if 'parquet' in valid_format:
        # Check for partial match for parquet and votable.parquet
        try:
            table_obj.export_table(filename,
                                   format=valid_format,
                                   overwrite=True)
            assert os.path.isfile(filename)
        except ModuleNotFoundError as me:
            assert 'This is not a default dependency of jdaviz.' in str(me)

    elif 'asdf' in valid_format:
        # Check asdf
        table_obj.export_table(filename, format=valid_format)
        assert os.path.isfile(filename)
        with pytest.raises(FileExistsError, match=r'exists and overwrite=False'):
            table_obj.export_table(filename,
                                   format=valid_format,
                                   overwrite=False)

    else:
        table_obj.export_table(filename, format=valid_format)
        assert os.path.isfile(filename)
