import numpy as np
import pytest
import re
from unittest.mock import patch

from astropy import units as u
from astropy.nddata import StdDevUncertainty

from specutils import Spectrum, SpectrumList

from jdaviz.core.loaders.importers.spectrum_list.spectrum_list import (
    SpectrumListImporter,
    combine_lists_to_1d_spectrum
)

from jdaviz.conftest import FakeSpectrumListImporter, FakeSpectrumListConcatenatedImporter


def extract_wfss_info(spec):
    """
    Copied and pasted from spectrum_list.py for testing purposes. If the parsing changes
    then this will need to be updated.
    """
    header = spec.meta.get('header', {})
    exp_num = header.get('EXPGRPID', '0_0_0').split('_')[-2]
    source_id = str(spec.meta.get('source_id', ''))
    return exp_num, source_id


class TestSpectrumListImporter:

    def setup_importer_obj(self, config_helper, input_obj):
        self.sources_labels = ['1D Spectrum at index: 0',
                               '1D Spectrum at index: 1',
                               'Exposure 0, Source ID: 0000',
                               'Exposure 0, Source ID: 1111',
                               'Exposure 1, Source ID: 1111']

        self.sources_data_labels = ['1D Spectrum_index-0',
                                    '1D Spectrum_index-1',
                                    '1D Spectrum_EXP-0_ID-0000',
                                    '1D Spectrum_EXP-0_ID-1111',
                                    '1D Spectrum_EXP-1_ID-1111']

        return FakeSpectrumListImporter(app=config_helper.app,
                                        resolver=config_helper.loaders['object']._obj,
                                        input=input_obj)

    def test_spectrum_list_importer_init_attributes(self, specviz_helper, deconfigged_helper,
                                                    premade_spectrum_list):
        importer_obj = self.setup_importer_obj(specviz_helper, premade_spectrum_list[0])
        assert importer_obj.data_label_default == '1D Spectrum'

        importer_obj = self.setup_importer_obj(deconfigged_helper, premade_spectrum_list)
        assert importer_obj.data_label_default == '1D Spectrum'
        assert hasattr(importer_obj, 'sources_items')
        assert hasattr(importer_obj, 'sources_selected')
        assert hasattr(importer_obj, 'sources_multiselect')
        assert hasattr(importer_obj, 'disable_dropdown')
        assert hasattr(importer_obj, 'sources')

        assert importer_obj.sources.selected == [importer_obj.sources.choices[0]]
        assert importer_obj._sources_items_helper == importer_obj.sources.items

    # Parameterize to test both single and multiple selection
    @pytest.mark.parametrize('to_select', [['1D Spectrum at index: 1'],
                                           ['1D Spectrum at index: 0',
                                            '1D Spectrum at index: 1',
                                            'Exposure 0, Source ID: 0000',
                                            'Exposure 1, Source ID: 1111']])
    def test_spectrum_list_importer_init_select(self, deconfigged_helper, premade_spectrum_list,
                                                spectrum1d, to_select):
        importer_obj = self.setup_importer_obj(deconfigged_helper, premade_spectrum_list)
        importer_obj.sources.selected = to_select

        assert hasattr(importer_obj.sources, 'items')
        assert hasattr(importer_obj.sources, 'selected')
        assert hasattr(importer_obj.sources, 'multiselect')
        assert hasattr(importer_obj.sources, 'manual_options')

        for index, (spec_dict, spec) in enumerate(
                zip(importer_obj.sources.manual_options, premade_spectrum_list)):

            # offset to account for 0 based indexing
            file_index = str(index)

            # ver, name are stand-ins for exposure and source_id
            # ver == exposure, name == source_id
            if len(spec.meta):
                ver, name = extract_wfss_info(spec)
            else:
                ver, name = str(index), str(index)

            spec_keys = {
                'label': [f"Exposure {ver}, Source ID: {name}",
                          f"1D Spectrum at index: {file_index}"],
                'name': [name, file_index],
                'ver': [ver, file_index],
                'name_ver': [f"{ver}_{name}", file_index],
                'index': [index, index],
                'suffix': [f"EXP-{ver}_ID-{name}", f"index-{file_index}"],
                'obj': None}

            assert isinstance(spec_dict, dict)
            assert len(spec_keys) == len(spec_dict)
            for key in spec_keys:
                assert key in spec_dict
                if key != 'obj':
                    assert spec_dict[key] in spec_keys[key]

            assert isinstance(spec_dict['obj'], Spectrum)
            mask = premade_spectrum_list[index].spectral_axis.mask
            assert np.all(spec_dict['obj'].flux ==
                          premade_spectrum_list[index].flux[~mask])
            assert np.all(spec_dict['obj'].spectral_axis ==
                          premade_spectrum_list[index].spectral_axis[~mask])

        # TODO: This triggers the strictly increasing/decreasing error
        # assert SpectrumList(spec_dict['obj']) == spectrum_list

    # Method tests
    def test_is_valid(self, deconfigged_helper, premade_spectrum_list,
                      spectrum1d, spectrum2d,
                      make_empty_spectrum, spectrum_collection):
        importer_obj = self.setup_importer_obj(deconfigged_helper, premade_spectrum_list)
        assert importer_obj.is_valid

        importer_obj.input = make_empty_spectrum
        assert not importer_obj.is_valid

        importer_obj.input = spectrum1d
        assert not importer_obj.is_valid

        importer_obj.input = spectrum2d
        assert importer_obj.is_valid

        importer_obj.input = spectrum_collection
        assert importer_obj.is_valid

    def test_on_sources_selected(self, deconfigged_helper, premade_spectrum_list):
        importer_obj = self.setup_importer_obj(deconfigged_helper, premade_spectrum_list)
        # Baseline, default first source selected
        assert importer_obj.sources.selected == [importer_obj.sources.choices[0]]
        assert importer_obj.import_disabled is False

        # Selecting the same thing shouldn't turn off the default flag
        importer_obj.sources.selected = [importer_obj.sources.choices[0]]
        assert importer_obj.import_disabled is False

        importer_obj.sources.selected = []
        assert importer_obj.import_disabled is True

    def test_on_format_selected(self, deconfigged_helper, premade_spectrum_list):
        importer_obj = self.setup_importer_obj(deconfigged_helper, premade_spectrum_list)

        # Baseline, default first source selected
        assert importer_obj.import_disabled is False
        assert importer_obj.sources.selected == [importer_obj.sources.choices[0]]
        importer_obj._on_format_selected_change(change={'new': '1D Spectrum List'})
        # No change
        assert importer_obj.import_disabled is False

        # Set new selection to empty to ensure it doesn't change on format change
        importer_obj.sources.selected = []
        importer_obj._on_format_selected_change(change={'new': '1D Spectrum List'})
        # No selection
        assert importer_obj.import_disabled is True

        # Still no selection
        importer_obj._on_format_selected_change(change={'new': '1D Spectrum Concatenated'})
        assert importer_obj.import_disabled is True

        importer_obj.sources.selected = importer_obj.sources.choices[:2]
        importer_obj._on_format_selected_change(change={'new': '1D Spectrum List'})
        assert importer_obj.import_disabled is False

        # No new selection
        importer_obj._on_format_selected_change(change={'new': '1D Spectrum Concatenated'})
        assert importer_obj.import_disabled is False

        importer_obj._on_format_selected_change(change={'new': 'Not a 1D Spectrum List'})
        assert importer_obj.import_disabled is False

    def test_on_format_selected_2d(self, deconfigged_helper, spectrum2d):
        importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum2d)

        # Baseline, single source selected
        assert importer_obj.import_disabled is False
        importer_obj._on_format_selected_change(change={'new': '1D Spectrum List'})
        # No change
        assert importer_obj.import_disabled is False

        # Reset to no selection
        importer_obj.sources.selected = []
        assert importer_obj.import_disabled is True

        # For 2d spectra, changing format does not change selection, but
        # we specifically enable the import button for 1D Spectrum Concatenated
        importer_obj._on_format_selected_change(change={'new': '1D Spectrum Concatenated'})
        assert importer_obj.import_disabled is False

        importer_obj._on_format_selected_change(change={'new': 'Not a 1D Spectrum List'})
        assert importer_obj.import_disabled is False

    def test_input_to_list_of_spec(self, deconfigged_helper, premade_spectrum_list):
        importer_obj = self.setup_importer_obj(deconfigged_helper, premade_spectrum_list)

        # Test the whole list
        list_results = list(importer_obj.input_to_list_of_spec(premade_spectrum_list))
        assert len(list_results) == len(premade_spectrum_list)
        assert all(isinstance(spec, Spectrum) for spec in list_results)

        # Test individual sources
        for i, spec in enumerate(premade_spectrum_list):
            results = importer_obj.input_to_list_of_spec(spec)
            assert isinstance(results, list)

            result_spec = results[0]
            assert isinstance(result_spec, Spectrum)

            spectral_axis = spec.spectral_axis
            mask = spectral_axis.mask
            # Check both the individual spectra and the results from performing
            # the operation on the whole list
            for result in (result_spec, list_results[i]):
                assert np.all(result.flux == spec.flux[~mask])
                assert np.all(result.spectral_axis == spectral_axis[~mask])
                assert np.all(result.uncertainty.array == spec.uncertainty[~mask].array)
                assert np.all(result.mask == mask[~mask])

    def test_input_to_list_of_spec_not_supported(self, deconfigged_helper, premade_spectrum_list):
        importer_obj = self.setup_importer_obj(deconfigged_helper, premade_spectrum_list)
        with pytest.raises(NotImplementedError, match='not_a_spectrum is not supported'):
            importer_obj.input_to_list_of_spec('not_a_spectrum')

    def test_is_wfssmulti(self, deconfigged_helper, premade_spectrum_list, wfss_spectrum1d):
        importer_obj = self.setup_importer_obj(deconfigged_helper, premade_spectrum_list)
        assert importer_obj.is_wfssmulti(wfss_spectrum1d)

    def test_extract_exposure_sourceid(self, deconfigged_helper, premade_spectrum_list,
                                       wfss_spectrum1d, partially_masked_wfss_spectrum1d,
                                       partially_masked_wfss_spectrum1d_exp1):
        importer_obj = self.setup_importer_obj(deconfigged_helper, premade_spectrum_list)
        exposure, source_id = importer_obj._extract_exposure_sourceid(wfss_spectrum1d)
        assert exposure == '0'
        assert source_id == '0000'

        exposure, source_id = importer_obj._extract_exposure_sourceid(
            partially_masked_wfss_spectrum1d)
        assert exposure == '0'
        assert source_id == '1111'

        exposure, source_id = importer_obj._extract_exposure_sourceid(
            partially_masked_wfss_spectrum1d_exp1)
        assert exposure == '1'
        assert source_id == '1111'

    def test_has_mask(self, deconfigged_helper, premade_spectrum_list, make_empty_spectrum):
        importer_obj = self.setup_importer_obj(deconfigged_helper, premade_spectrum_list)

        # Even unmasked sources still *have* a mask, it's just all False
        for spec in premade_spectrum_list:
            assert importer_obj._has_mask(spec) is True

        assert importer_obj._has_mask(make_empty_spectrum) is False

        make_empty_spectrum.mask = None
        assert importer_obj._has_mask(make_empty_spectrum) is False

    def test_is_fully_masked(self, deconfigged_helper, premade_spectrum_list, spectrum1d):
        importer_obj = self.setup_importer_obj(deconfigged_helper, premade_spectrum_list)

        assert importer_obj._is_fully_masked(spectrum1d) is False
        spectrum1d.mask[:] = True
        assert importer_obj._is_fully_masked(spectrum1d) is True

    def test_is_2d_spectrum(self, deconfigged_helper, spectrum1d, spectrum2d):
        importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum2d)
        assert importer_obj._is_2d_spectrum is True

        importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum1d)
        assert importer_obj._is_2d_spectrum is False

    def test_apply_spectral_mask(self, deconfigged_helper, premade_spectrum_list,
                                 make_empty_spectrum, spectrum1d,
                                 partially_masked_wfss_spectrum1d):
        importer_obj = self.setup_importer_obj(deconfigged_helper, premade_spectrum_list)
        # This does not have a spectral axis mask so it should return as is
        result = importer_obj._apply_spectral_mask(make_empty_spectrum)
        assert result is make_empty_spectrum

        # This doesn't necessarily test something in the spectrum_list code,
        # but it's an error that we should be aware of.
        with pytest.raises(ValueError,
                           match='Spectral axis must be strictly increasing or decreasing.'):
            spectrum1d.spectral_axis.mask[:] = True
            _ = importer_obj._apply_spectral_mask(spectrum1d)

        spec = partially_masked_wfss_spectrum1d
        mask = spec.spectral_axis.mask
        result = importer_obj._apply_spectral_mask(spec)
        assert np.all(result.flux == spec.flux[~mask])
        assert np.all(result.spectral_axis == spec.spectral_axis[~mask])
        assert np.all(result.uncertainty.array == spec.uncertainty[~mask].array)
        assert np.all(result.mask == mask[~mask])

    def test_apply_kwargs(self, deconfigged_helper, premade_spectrum_list):
        importer_obj = self.setup_importer_obj(deconfigged_helper, premade_spectrum_list)

        warning_msg = (
            f"The default source selection ({importer_obj.sources.selected}) will be used.\n"
            f"To load additional sources, please specify them via dropdown or "
            f"as follows:\n'{importer_obj.config}.load(filename, sources = [...]).")

        # Mock the broadcast method to catch the snackbar messages
        with patch.object(deconfigged_helper.app.hub, 'broadcast') as mock_broadcast:
            with pytest.warns(UserWarning, match=re.escape(warning_msg)):
                importer_obj._apply_kwargs({})

            broadcast_msgs = [arg[0][0].text for arg in mock_broadcast.call_args_list
                              if hasattr(arg[0][0], 'text')]
            assert warning_msg in broadcast_msgs

        # No warning this time
        with patch.object(deconfigged_helper.app.hub, 'broadcast') as mock_broadcast:
            importer_obj._apply_kwargs({'sources': ['1D Spectrum at index: 1']})
            assert mock_broadcast.call_count == 0

    def test_output(self, deconfigged_helper, premade_spectrum_list, spectrum1d):
        importer_obj = self.setup_importer_obj(deconfigged_helper, premade_spectrum_list)
        # Must make a selection for output to work
        importer_obj.sources.selected = '1D Spectrum at index: 0'
        assert isinstance(importer_obj.output, list)

        # Check that these are indeed the same
        spec_dict = importer_obj.sources.manual_options[0]
        assert importer_obj.output[0] == spec_dict['obj']

        # Check that is_valid is enforced in the output
        importer_obj.input = spectrum1d
        assert importer_obj.output is None

    @pytest.mark.parametrize('selection', [[],
                                           '1D Spectrum at index: *',
                                           ['1D Spectrum at index: 0',
                                            '1D Spectrum at index: 1',
                                            'Exposure 0, Source ID: 1111',
                                            'Exposure 1, Source ID: 1111']])
    def test_call_method_basic(self, deconfigged_helper, premade_spectrum_list, selection):
        importer_obj = self.setup_importer_obj(deconfigged_helper, premade_spectrum_list)
        sources_data_labels = self.sources_data_labels

        if not selection:
            importer_obj.user_api.sources = selection
            error_msg = "No sources selected."
            # Checking with no selection yet, raises error
            with pytest.raises(
                    ValueError,
                    match=re.escape(error_msg)):
                importer_obj.__call__()

            # Load all anyway
            importer_obj.sources.select_all()
            importer_obj.__call__()
            dc_len = 5
        else:
            importer_obj.user_api.sources = selection
            importer_obj.__call__()
            if isinstance(selection, str):
                dc_len = 2
                sources_data_labels = sources_data_labels[:2]
            elif isinstance(selection, list):
                dc_len = len(selection)
                sources_data_labels = sources_data_labels[:2] + sources_data_labels[-2:]

        # Data collection items
        dc = deconfigged_helper.app.data_collection
        assert len(dc) == dc_len  # number of sources loaded

        assert all([label in sources_data_labels for label in dc.labels])

        # Viewer items
        viewers = deconfigged_helper.viewers
        assert len(viewers) == 1
        assert '1D Spectrum' in viewers

        viewer_dm = viewers['1D Spectrum'].data_menu

        # Note: in a previous version of this test, sources object had a duplicate label hence->
        # TODO: should these be in sync with data collection?
        #  If there is a duplicate data label, it gets overwritten in the viewer
        #  but the data collection will have both.
        assert len(viewer_dm.data_labels_loaded) == len(sources_data_labels)
        assert all([label in sources_data_labels for label in viewer_dm.data_labels_loaded])
        assert len(viewer_dm.data_labels_visible) == len(sources_data_labels)
        assert all([label in sources_data_labels for label in viewer_dm.data_labels_visible])


@pytest.mark.parametrize('with_uncertainty', [True, False])
def test_combine_lists_to_1d_spectrum(with_uncertainty):
    wl = [1, 2, 3] * u.nm
    fnu = [10, 20, 30] * u.Jy
    if with_uncertainty:
        dfnu = [4, 5, 6] * u.Jy
    else:
        dfnu = None

    spec = combine_lists_to_1d_spectrum(wl, fnu, dfnu, u.nm, u.Jy)
    assert isinstance(spec, Spectrum)
    assert isinstance(spec.flux, u.Quantity)
    assert spec.flux.unit == u.Jy

    assert isinstance(spec.spectral_axis, u.Quantity)
    assert spec.spectral_axis.unit == u.nm

    assert np.all(spec.flux.value == np.array([10, 20, 30]))
    assert np.all(spec.spectral_axis.value == np.array([1, 2, 3]))

    if with_uncertainty:
        assert isinstance(spec.uncertainty, StdDevUncertainty)
        assert np.all(spec.uncertainty.array == np.array([4, 5, 6]))
    else:
        assert spec.uncertainty is None


class TestSpectrumListConcatenatedImporter:

    @staticmethod
    def setup_importer_obj(config_helper, input_obj):
        return FakeSpectrumListConcatenatedImporter(app=config_helper.app,
                                                    resolver=config_helper.loaders['object']._obj,
                                                    input=input_obj)

    def setup_combined_spectrum(self, with_uncertainty):
        wl = [1, 2, 3] * u.nm
        fnu = [10, 20, 30] * u.Jy
        if with_uncertainty:
            dfnu = [4, 5, 6] * u.Jy
        else:
            dfnu = None
        return combine_lists_to_1d_spectrum(wl, fnu, dfnu, u.nm, u.Jy)

    @pytest.mark.parametrize('use_list', [True, False])
    def test_spectrum_list_concatenated_importer_init(self, deconfigged_helper,
                                                      spectrum2d, premade_spectrum_list,
                                                      use_list):
        if use_list:
            importer_obj = self.setup_importer_obj(deconfigged_helper, premade_spectrum_list)
            # Without this, the test gets stuck on the call to importer_obj.output
            # I have not been able to replicate the behavior outside the tests,
            # so I am leaving this test as-is for now.
            importer_obj.sources.selected = []
            assert importer_obj.import_disabled is True
        else:
            importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum2d)
            # Just in case the order is different
            assert len(set(importer_obj.user_api.sources.selected).difference(set(importer_obj.sources.choices))) == 0 # noqa
            assert importer_obj.import_disabled is False

        assert isinstance(importer_obj, SpectrumListImporter)
        # Sneaky negation of boolean to test the disable_dropdown attribute
        assert importer_obj.disable_dropdown is not use_list

        # ensure native units on surface brightness or spectral flux density are converted to flux
        if use_list:
            assert np.all([sp.flux.unit.physical_type == 'spectral flux density'
                           for sp in premade_spectrum_list])
            assert np.all([sp.flux.unit.physical_type == 'spectral flux density'
                           for sp in importer_obj.output])
        else:
            assert spectrum2d.flux.unit.physical_type == 'spectral flux density'
            assert u.Unit(importer_obj.output.flux.unit.to_string()).physical_type == 'spectral flux density' # noqa

    @pytest.mark.parametrize('with_uncertainty', [True, False])
    def test_spectrum_list_concatenated_importer_output(self, deconfigged_helper, with_uncertainty):
        spec = self.setup_combined_spectrum(with_uncertainty)

        importer_obj = self.setup_importer_obj(deconfigged_helper, SpectrumList([spec]))
        result = importer_obj.output

        assert np.all(result.flux == spec.flux)
        assert np.all(result.spectral_axis == spec.spectral_axis)
        if with_uncertainty:
            assert np.all(result.uncertainty.array == spec.uncertainty.array)

    def test_spectrum_list_concatenated_importer_output_empty(self, deconfigged_helper):
        spec = self.setup_combined_spectrum(with_uncertainty=True)

        importer_obj = self.setup_importer_obj(deconfigged_helper, SpectrumList([spec]))
        importer_obj.sources.selected = []
        assert len(importer_obj.output) == 0

    def test_spectrum_list_concatenated_importer_output_default(self, deconfigged_helper):
        spec = self.setup_combined_spectrum(with_uncertainty=True)

        importer_obj = self.setup_importer_obj(deconfigged_helper, SpectrumList([spec]))
        result = importer_obj.output
        assert np.all(result.flux == spec.flux)
        assert np.all(result.spectral_axis == spec.spectral_axis)
        assert np.all(result.uncertainty.array == spec.uncertainty.array)

    def test_spectrum_list_concatenated_importer_output_2d(self, deconfigged_helper, spectrum2d):
        importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum2d)
        _ = importer_obj.output
        assert importer_obj.disable_dropdown is True
        for selected in importer_obj.sources.selected:
            assert isinstance(selected, str)
            assert selected in importer_obj.sources.choices

    def test_spectrum_list_concatenated_importer_call(self, deconfigged_helper):
        spec = self.setup_combined_spectrum(with_uncertainty=True)

        importer_obj = self.setup_importer_obj(deconfigged_helper, SpectrumList([spec]))
        importer_obj.__call__()

        dc = deconfigged_helper.app.data_collection
        assert len(dc) == 1  # 1 concatenated spectrum loaded
        result = dc[0].get_object()

        assert np.all(result.flux == spec.flux)
        assert np.all(result.spectral_axis == spec.spectral_axis)
        assert np.all(result.uncertainty.array == spec.uncertainty.array)
