import numpy as np
import pytest
from unittest.mock import patch

from astropy import units as u
from astropy.utils.masked import Masked
from astropy.nddata import StdDevUncertainty

from specutils import Spectrum, SpectrumList, SpectrumCollection

from jdaviz.core.loaders.importers.spectrum_list.spectrum_list import (
    SpectrumListImporter,
    SpectrumListConcatenatedImporter,
    combine_lists_to_1d_spectrum
)
from jdaviz.core.registries import loader_importer_registry


def make_spectrum(spectral_mask=None, wfss=False, collection=False,
                  exposure='0_0_0_1', source_id='0000'):
    cls = Spectrum
    meta = {}
    spec_len = 5
    # Flux is not a masked array, only spectral axis
    flux = np.arange(spec_len) * u.Jy

    if spectral_mask is None:
        spectral_mask = np.array([False] * spec_len)

    spectral_axis = Masked(np.arange(spec_len) * u.nm, mask=spectral_mask)
    uncertainty = StdDevUncertainty(flux)

    if wfss:
        meta = {'header': {'DATAMODL': 'WFSSMulti', 'EXPGRPID': exposure}, 'source_id': source_id}

    if collection:
        cls = SpectrumCollection

    return cls(flux=flux, spectral_axis=spectral_axis,
               uncertainty=uncertainty, mask=spectral_mask,
               meta=meta)


def extract_wfss_info(spec):
    """
    Copied and pasted from spectrum_list.py for testing purposes. If the parsing changes
    then this will need to be updated.
    """
    header = spec.meta.get('header', {})
    exp_num = header.get('EXPGRPID', '0_0_0').split('_')[-2]
    source_id = spec.meta.get('source_id', '')

    return exp_num, source_id


@pytest.fixture
def make_empty_spectrum():
    return Spectrum(spectral_axis=np.array([]) * u.Hz,
                    flux=np.array([]) * u.Jy,
                    uncertainty=StdDevUncertainty(np.array([])),
                    mask=np.array([]),
                    meta={})


@pytest.fixture
def unmasked_spectrum():
    return make_spectrum()


@pytest.fixture
def partially_masked_spectrum():
    return make_spectrum(spectral_mask=np.array([False, False, False, True, True]))


@pytest.fixture
def wfss_spectrum():
    return make_spectrum(wfss=True)


# WFSS may have spectral axes that are partially masked
# and this is not allowed in specutils
@pytest.fixture
def partially_masked_wfss_spectrum():
    return make_spectrum(spectral_mask=np.array([False, False, False, True, True]), wfss=True,
                         source_id='1111')


@pytest.fixture
def unmasked_2d_spectrum():
    spec_len = 10
    flux = np.ones((2, spec_len)) * u.Jy
    spectral_axis = np.arange(spec_len) * u.nm
    return Spectrum(flux=flux, spectral_axis=spectral_axis)


@pytest.fixture
def spectrum_list(unmasked_spectrum, partially_masked_spectrum,
                  wfss_spectrum, partially_masked_wfss_spectrum):
    return SpectrumList([
        unmasked_spectrum,
        partially_masked_spectrum,
        wfss_spectrum,
        partially_masked_wfss_spectrum])


@loader_importer_registry('Test Fake 1D Spectrum List')
class FakeImporter(SpectrumListImporter):
    """A fake importer for testing/convenience purposes only.
    Mostly used to hot-update input for clean code/speed purposes."""
    template = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.new_default_data_label = None

    @property
    def input(self):
        return super().input

    @input.setter
    def input(self, value):
        self._input = value

    @property
    def default_data_label_from_resolver(self):
        if hasattr(self, 'new_default_data_label'):
            return self.new_default_data_label
        return None


class TestSpectrumListImporter:

    @staticmethod
    def setup_importer_obj(config_helper, input_obj):
        return FakeImporter(app=config_helper.app,
                            resolver=config_helper.loaders['object']._obj,
                            input=input_obj)

    def test_spectrum_list_importer_init_attributes(self, specviz_helper, deconfigged_helper,
                                                    spectrum_list):
        importer_obj = self.setup_importer_obj(specviz_helper, spectrum_list[0])
        assert importer_obj.data_label_default == '1D Spectrum'

        importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)
        assert importer_obj.data_label_default == '1D Spectrum'
        assert hasattr(importer_obj, 'spectra_items')
        assert hasattr(importer_obj, 'spectra_selected')
        assert hasattr(importer_obj, 'spectra_multiselect')
        assert hasattr(importer_obj, 'disable_dropdown')
        assert hasattr(importer_obj, 'spectra')

        assert importer_obj.fully_masked_spectra == []
        assert importer_obj.spectra.selected == []
        assert importer_obj.previous_data_label_messages == []

    # Parameterize to test both single and multiple selection
    @pytest.mark.parametrize('to_select', [['1D Spectrum at file index: 1'],
                                           ['1D Spectrum at file index: 1',
                                            '1D Spectrum at file index: 2',
                                            'Exposure 0, Source ID: 0000',
                                            'Exposure 0, Source ID: 1111']])
    def test_spectrum_list_importer_init_select(self, deconfigged_helper, spectrum_list,
                                                to_select):
        # Set up a fully masked spectrum
        new_spectra = make_spectrum()
        new_spectra.mask[:] = True
        # This will help us to confirm that masked spectra are skipped
        # and that the indices are correct per the modifier
        new_spectrum_list = SpectrumList([new_spectra] + spectrum_list)

        importer_obj = self.setup_importer_obj(deconfigged_helper, new_spectrum_list)
        importer_obj.spectra.selected = to_select

        assert importer_obj.fully_masked_spectra == ['1D Spectrum_file_index-0']
        assert hasattr(importer_obj.spectra, 'items')
        assert hasattr(importer_obj.spectra, 'selected')
        assert hasattr(importer_obj.spectra, 'multiselect')
        assert hasattr(importer_obj.spectra, 'manual_options')

        for index, (spec_dict, spec) in enumerate(
                zip(importer_obj.spectra.manual_options, new_spectrum_list[1:])):

            # offset to account for the fully masked spectrum at the start
            file_index = str(index + 1)

            # ver, name are stand-ins for exposure and source_id
            # ver == exposure, name == source_id
            if len(spec.meta):
                ver, name = extract_wfss_info(spec)
            else:
                ver, name = str(index), str(index)

            keys = {
                'label': [f"Exposure {ver}, Source ID: {name}",
                          f"1D Spectrum at file index: {file_index}"],
                'name': [name, file_index],
                'ver': [ver, file_index],
                'name_ver': [f"{ver}_{name}", file_index],
                'index': [index, index],
                '_suffix': [f"EXP-{ver}_ID-{name}", f"file_index-{file_index}"],
                'obj': None}

            assert isinstance(spec_dict, dict)
            assert set(keys.keys()).issubset(set(spec_dict.keys()))
            for key in keys:
                if key != 'obj':
                    assert spec_dict[key] in keys[key]

            assert isinstance(spec_dict['obj'], Spectrum)
            mask = spectrum_list[index].spectral_axis.mask
            assert np.all(spec_dict['obj'].flux ==
                          spectrum_list[index].flux[~mask])
            assert np.all(spec_dict['obj'].spectral_axis ==
                          spectrum_list[index].spectral_axis[~mask])

        # TODO: This triggers the strictly increasing/decreasing error
        # assert SpectrumList(spec_dict['obj']) == spectrum_list

    # Method tests
    def test_is_valid(self, deconfigged_helper, spectrum_list,
                      unmasked_spectrum, unmasked_2d_spectrum,
                      make_empty_spectrum):
        importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)
        assert importer_obj.is_valid

        importer_obj.input = make_empty_spectrum
        assert not importer_obj.is_valid

        importer_obj.input = unmasked_spectrum
        assert not importer_obj.is_valid

        importer_obj.input = unmasked_2d_spectrum
        assert importer_obj.is_valid

        importer_obj.input = make_spectrum(collection=True)
        assert importer_obj.is_valid

    def test_on_spectra_selected(self, deconfigged_helper, spectrum_list):
        importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)
        # Nothing has been selected yet
        assert importer_obj.resolver.import_disabled is True
        importer_obj.spectra.selected = importer_obj.spectra.choices[0]
        assert importer_obj.resolver.import_disabled is False

    def test_input_to_list_of_spec(self, deconfigged_helper, spectrum_list):
        importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)

        # Test the whole list
        list_results = list(importer_obj.input_to_list_of_spec(spectrum_list))
        assert len(list_results) == len(spectrum_list)
        assert all(isinstance(spec, Spectrum) for spec in list_results)

        # Test individual spectra
        for i, spec in enumerate(spectrum_list):
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

    def test_input_to_list_of_spec_not_supported(self, deconfigged_helper, spectrum_list):
        importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)
        with pytest.raises(NotImplementedError):
            importer_obj.input_to_list_of_spec('not_a_spectrum')

    def test_is_wfssmulti(self, deconfigged_helper, spectrum_list, wfss_spectrum):
        importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)
        assert importer_obj.is_wfssmulti(wfss_spectrum)

    def test_extract_exposure_sourceid(self, deconfigged_helper, spectrum_list,
                                       wfss_spectrum, partially_masked_wfss_spectrum):
        importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)
        exposure, source_id = importer_obj._extract_exposure_sourceid(wfss_spectrum)
        assert exposure == '0'
        assert source_id == '0000'

        exposure, source_id = importer_obj._extract_exposure_sourceid(
            partially_masked_wfss_spectrum)
        assert exposure == '0'
        assert source_id == '1111'

    def test_has_mask(self, deconfigged_helper, spectrum_list, make_empty_spectrum):
        importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)

        # Even unmasked spectra still *have* a mask, it's just all False
        for spec in spectrum_list:
            assert importer_obj._has_mask(spec)

        assert not importer_obj._has_mask(make_empty_spectrum)

        make_empty_spectrum.mask = None
        assert not importer_obj._has_mask(make_empty_spectrum)

    def test_is_fully_masked(self, deconfigged_helper, spectrum_list, unmasked_spectrum):
        importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)

        assert not importer_obj._is_fully_masked(unmasked_spectrum)
        unmasked_spectrum.mask[:] = True
        assert importer_obj._is_fully_masked(unmasked_spectrum)

    def test_apply_spectral_mask(self, deconfigged_helper, spectrum_list,
                                 make_empty_spectrum, unmasked_spectrum,
                                 partially_masked_wfss_spectrum):
        importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)
        # This does not have a spectral axis mask so it should return as is
        result = importer_obj._apply_spectral_mask(make_empty_spectrum)
        assert result is make_empty_spectrum

        # This doesn't necessarily test something in the spectrum_list code,
        # but it's an error that we should be aware of.
        with pytest.raises(ValueError,
                           match='Spectral axis must be strictly increasing or decreasing.'):
            unmasked_spectrum.spectral_axis.mask[:] = True
            _ = importer_obj._apply_spectral_mask(unmasked_spectrum)

        spec = partially_masked_wfss_spectrum
        mask = spec.spectral_axis.mask
        result = importer_obj._apply_spectral_mask(spec)
        assert np.all(result.flux == spec.flux[~mask])
        assert np.all(result.spectral_axis == spec.spectral_axis[~mask])
        assert np.all(result.uncertainty.array == spec.uncertainty[~mask].array)
        assert np.all(result.mask == mask[~mask])

    def test_output(self, deconfigged_helper, spectrum_list, unmasked_spectrum):
        importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)
        # Must make a selection for output to work
        importer_obj.spectra.selected = '1D Spectrum at file index: 0'
        assert isinstance(importer_obj.output, list)

        # Check that these are indeed the same
        spec_dict = importer_obj.spectra.manual_options[0]
        for k, v in importer_obj.output[0].items():
            assert v == spec_dict[k]

        # Check that is_valid is enforced in the output
        importer_obj.input = unmasked_spectrum
        assert importer_obj.output is None

    def test_default_viewer_reference(self, deconfigged_helper, spectrum_list):
        importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)
        assert importer_obj.default_viewer_reference == 'spectrum-1d-viewer'

    @pytest.mark.parametrize('selection', [[], ['1D Spectrum at file index: 0',
                                                '1D Spectrum at file index: 1',
                                                'Exposure 0, Source ID: 0000',
                                                'Exposure 0, Source ID: 1111']])
    def test_call_method_basic(self, deconfigged_helper, spectrum_list, selection):
        importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)
        importer_obj.input = spectrum_list
        importer_obj.spectra.selected = selection
        if not selection:
            # Checking with no selection yet, defaults to importing all spectra
            with pytest.warns(
                    UserWarning,
                    match='No spectra selected, defaulting to loading all spectra in the list.'):
                importer_obj.__call__()
        else:
            importer_obj.__call__()

        assert importer_obj.previous_data_label_messages == []

        # Data collection items
        dc = deconfigged_helper.app.data_collection
        assert len(dc) == 4  # 4 spectra loaded

        spectra_labels = ['1D Spectrum_file_index-0',
                          '1D Spectrum_file_index-1',
                          '1D Spectrum_EXP-0_ID-0000',
                          '1D Spectrum_EXP-0_ID-1111']

        assert all([label in spectra_labels for label in dc.labels])

        # Viewer items
        viewers = deconfigged_helper.viewers
        assert len(viewers) == 1
        assert '1D Spectrum' in viewers

        viewer = viewers['1D Spectrum']
        viewer_dm = viewer.data_menu

        for v in (viewer, viewer_dm):
            # Note: in a previous version of this test, spectra object had a duplicate label hence->
            # TODO: should these be in sync with data collection?
            #  If there is a duplicate data label, it gets overwritten in the viewer
            #  but the data collection will have both.
            assert len(v.data_labels_loaded) == len(spectra_labels)
            assert all([label in spectra_labels for label in v.data_labels_loaded])
            assert len(v.data_labels_visible) == len(spectra_labels)
            assert all([label in spectra_labels for label in v.data_labels_visible])

    def test_call_method_repeat_call(self, deconfigged_helper, spectrum_list):
        importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)
        importer_obj.input = spectrum_list
        with pytest.warns(
                UserWarning,
                match='No spectra selected, defaulting to loading all spectra in the list.'):
            importer_obj.__call__()

        spectra_labels = ['1D Spectrum_file_index-0',
                          '1D Spectrum_file_index-1',
                          '1D Spectrum_EXP-0_ID-0000',
                          '1D Spectrum_EXP-0_ID-1111']

        # Mock the broadcast method to catch the snackbar messages
        with patch.object(deconfigged_helper.app.hub, 'broadcast') as mock_broadcast:
            assert len(importer_obj.previous_data_label_messages) == 0
            importer_obj.__call__()
            assert len(importer_obj.previous_data_label_messages) == 4

            expected_messages = [(f"Spectrum with label '{label}' "
                                  f"already exists in the viewer, skipping. "
                                  f"This message will only be shown once.")
                                 for label in spectra_labels]
            broadcast_msgs = [arg[0][0].text for arg in mock_broadcast.call_args_list
                              if hasattr(arg[0][0], 'text')]
            assert all([msg in broadcast_msgs for msg in expected_messages])

            # One more time to verify that no more messages are added
            importer_obj.__call__()
            assert len(importer_obj.previous_data_label_messages) == 4

            broadcast_msgs_final = set([arg[0][0].text for arg in mock_broadcast.call_args_list
                                        if hasattr(arg[0][0], 'text')])
            assert len(broadcast_msgs_final) == len(broadcast_msgs)

        # Viewer items
        # This implicitly tests the parenting logic but since that logic may change,
        # it is not worth making that explicit here.
        viewers = deconfigged_helper.viewers
        assert len(viewers) == 1
        assert '1D Spectrum' in viewers

        viewer = viewers['1D Spectrum']
        viewer_dm = viewer.data_menu

        for v in (viewer, viewer_dm):
            assert len(v.data_labels_loaded) == len(spectra_labels)
            assert all([label in spectra_labels for label in v.data_labels_loaded])
            assert len(v.data_labels_visible) == len(spectra_labels)
            assert all([label in spectra_labels for label in v.data_labels_visible])

    def test_call_method_different_data(self, deconfigged_helper,
                                        spectrum_list, unmasked_2d_spectrum):
        importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)
        importer_obj.input = spectrum_list
        with pytest.warns(
                UserWarning,
                match='No spectra selected, defaulting to loading all spectra in the list.'):
            importer_obj.__call__()

        importer_obj.new_default_data_label = '2D Spectrum'
        importer_obj.__init__(app=deconfigged_helper.app,
                              resolver=deconfigged_helper.loaders['object']._obj,
                              input=unmasked_2d_spectrum)

        assert importer_obj.data_label_default == '2D Spectrum'

        importer_obj.data_label_value = '2D_Spectrum'
        importer_obj.spectra.selected = ['2D Spectrum at file index: 0',
                                         '2D Spectrum at file index: 1']
        importer_obj.__call__()

        spectra_labels = ['1D Spectrum_file_index-0',
                          '1D Spectrum_file_index-1',
                          '1D Spectrum_EXP-0_ID-0000',
                          '1D Spectrum_EXP-0_ID-1111',
                          '2D_Spectrum_file_index-0',
                          '2D_Spectrum_file_index-1']

        assert all([label in deconfigged_helper.app.data_collection.labels
                    for label in spectra_labels])

        # Viewer items
        viewers = deconfigged_helper.viewers
        # TODO: Two viewers is the intended behavior but this will need a future update to work
        # assert len(viewers) == 2
        for viewer in viewers.values():
            viewer_dm = viewer.data_menu

            for v in (viewer, viewer_dm):
                assert len(v.data_labels_loaded) == len(spectra_labels)
                assert all([label in spectra_labels for label in v.data_labels_loaded])
                assert len(v.data_labels_visible) == len(spectra_labels)
                assert all([label in spectra_labels for label in v.data_labels_visible])


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
    assert isinstance(spec.spectral_axis, u.Quantity)
    assert np.all(spec.flux.value == np.array([10, 20, 30]))
    assert np.all(spec.spectral_axis.value == np.array([1, 2, 3]))

    if with_uncertainty:
        assert isinstance(spec.uncertainty, StdDevUncertainty)
        assert np.all(spec.uncertainty.array == np.array([4, 5, 6]))


@loader_importer_registry('Test Fake 1D Spectrum List Concatenated')
class FakeConcatenatedImporter(SpectrumListConcatenatedImporter):
    """A fake importer for testing/convenience purposes only.
    Mostly used to hot-update input for clean code/speed purposes."""
    template = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.new_default_data_label = None

    @property
    def input(self):
        return super().input

    @input.setter
    def input(self, value):
        self._input = value

    @property
    def default_data_label_from_resolver(self):
        if hasattr(self, 'new_default_data_label'):
            return self.new_default_data_label
        return None


class TestSpectrumListConcatenatedImporter:

    @staticmethod
    def setup_importer_obj(config_helper, input_obj):
        return FakeConcatenatedImporter(app=config_helper.app,
                                        resolver=config_helper.loaders['object']._obj,
                                        input=input_obj)

    def test_spectrum_list_concatenated_importer_init(self, deconfigged_helper,
                                                      unmasked_2d_spectrum):
        importer_obj = self.setup_importer_obj(deconfigged_helper, unmasked_2d_spectrum)
        assert isinstance(importer_obj, SpectrumListImporter)
        assert importer_obj.disable_dropdown

    @pytest.mark.parametrize('with_uncertainty', [True, False])
    def test_spectrum_list_concatenated_importer_output(self, deconfigged_helper, with_uncertainty):
        wl = [1, 2, 3] * u.nm
        fnu = [10, 20, 30] * u.Jy
        if with_uncertainty:
            dfnu = [4, 5, 6] * u.Jy
        else:
            dfnu = None
        spec = combine_lists_to_1d_spectrum(wl, fnu, dfnu, u.nm, u.Jy)

        importer_obj = self.setup_importer_obj(deconfigged_helper, SpectrumList([spec]))
        result = importer_obj.output
        assert np.all(result.flux == spec.flux)
        assert np.all(result.spectral_axis == spec.spectral_axis)
        if with_uncertainty:
            assert np.all(result.uncertainty.array == spec.uncertainty.array)

    def test_spectrum_list_concatenated_importer_call(self, deconfigged_helper,
                                                      unmasked_2d_spectrum):
        wl = [1, 2, 3] * u.nm
        fnu = [10, 20, 30] * u.Jy
        dfnu = [4, 5, 6] * u.Jy
        spec = combine_lists_to_1d_spectrum(wl, fnu, dfnu, u.nm, u.Jy)

        importer_obj = self.setup_importer_obj(deconfigged_helper, SpectrumList([spec]))
        importer_obj.__call__()

        dc = deconfigged_helper.app.data_collection
        assert len(dc) == 1  # 1 concatenated spectrum loaded
        result = dc[0].get_object()

        assert np.all(result.flux == spec.flux)
        assert np.all(result.spectral_axis == spec.spectral_axis)
        assert np.all(result.uncertainty.array == spec.uncertainty.array)
