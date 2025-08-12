import numpy as np
import pytest
from astropy import units as u
from astropy.utils.masked import Masked
from astropy.nddata import StdDevUncertainty

from specutils import Spectrum, SpectrumList, SpectrumCollection

from jdaviz.core.loaders.importers.spectrum_list.spectrum_list import (
    SpectrumListImporter,
    combine_lists_to_1d_spectrum
)

from jdaviz.core.registries import loader_importer_registry

@pytest.fixture
def make_empty_spectrum():
    return Spectrum(spectral_axis=np.array([]) * u.Hz,
                    flux=np.array([]) * u.Jy,
                    uncertainty=StdDevUncertainty(np.array([])),
                    mask=np.array([]),
                    meta={})


def make_spectrum(spectral_mask=None, wfss=False, collection=False):
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
        meta = {'header': {'DATAMODL': 'WFSSMulti', 'EXPGRPID': '0_0_0_1'}, 'source_id': '1111'}

    if collection:
        cls = SpectrumCollection

    return cls(flux=flux, spectral_axis=spectral_axis,
               uncertainty=uncertainty, mask=spectral_mask,
               meta=meta)


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
    return make_spectrum(spectral_mask=np.array([False, False, False, True, True]), wfss=True)


@pytest.fixture
def unmasked_2d_spectrum():
    flux = np.ones((2, 5)) * u.Jy
    spectral_axis = np.arange(5) * u.nm
    return Spectrum(flux=flux, spectral_axis=spectral_axis)


@pytest.fixture
def spectrum_list(unmasked_spectrum, partially_masked_spectrum,
                  wfss_spectrum, partially_masked_wfss_spectrum):
    return SpectrumList([
        unmasked_spectrum,
        partially_masked_spectrum,
        wfss_spectrum,
        partially_masked_wfss_spectrum])


@loader_importer_registry('Fake 1D Spectrum List')
class FakeImporter(SpectrumListImporter):
    """A fake importer for testing/convenience purposes only.
    Mostly used to hot-update input for clean code/speed purposes."""
    template = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def input(self):
        return super().input

    @input.setter
    def input(self, value):
        self._input = value


class TestSpectrumListImporter:

    @staticmethod
    def setup_importer_obj(config_helper, input_obj):
        # ldr = config_helper.loaders['object']
        # # The resolver is ldr._obj. Set the restriction before loading the object.
        # ldr.object = ldr_object
        # return ldr, ldr.importer
        return FakeImporter(app=config_helper.app,
                            resolver=config_helper.loaders['object']._obj,
                            input=input_obj)

    def test_spectrum_list_importer_attributes(self, specviz_helper, deconfigged_helper, spectrum_list):
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

            result = results[0]
            assert isinstance(result, Spectrum)

            spectral_axis = spec.spectral_axis
            mask = spectral_axis.mask
            assert np.all(result.flux == spec.flux[~mask])
            assert np.all(result.spectral_axis == spectral_axis[~mask])
            assert np.all(result.uncertainty.array == spec.uncertainty[~mask].array)
            assert np.all(result.mask == mask[~mask])

            list_result = list_results[i]
            assert np.all(list_result.flux == spec.flux[~mask])
            assert np.all(list_result.spectral_axis == spectral_axis[~mask])
            assert np.all(list_result.uncertainty.array == spec.uncertainty[~mask].array)
            assert np.all(list_result.mask == mask[~mask])

    def test_input_to_list_of_spec_not_supported(self, deconfigged_helper, spectrum_list):
        importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)
        with pytest.raises(NotImplementedError):
            importer_obj.input_to_list_of_spec('not_a_spectrum')

    def test_is_wfssmulti(self, deconfigged_helper, spectrum_list, wfss_spectrum):
        importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)
        assert importer_obj.is_wfssmulti(wfss_spectrum)

    def test_extract_exposure_sourceid(self, deconfigged_helper, spectrum_list, wfss_spectrum):
        importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)
        exposure, source_id = importer_obj.extract_exposure_sourceid(wfss_spectrum)
        assert exposure == '0'
        assert source_id == '1111'

    def test_has_mask(self, deconfigged_helper, spectrum_list, make_empty_spectrum):
        importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)

        # Even unmasked spectra still *have* a mask, it's just all False
        for spec in spectrum_list:
            assert importer_obj.has_mask(spec)

        assert not importer_obj.has_mask(make_empty_spectrum)

        make_empty_spectrum.mask = None
        assert not importer_obj.has_mask(make_empty_spectrum)

    def test_is_fully_masked(self, deconfigged_helper, spectrum_list, unmasked_spectrum):
        importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)

        assert not importer_obj.is_fully_masked(unmasked_spectrum)
        unmasked_spectrum.mask[:] = True
        assert importer_obj.is_fully_masked(unmasked_spectrum)

    def test_apply_spectral_mask(self, deconfigged_helper, spectrum_list,
                                 make_empty_spectrum, unmasked_spectrum,
                                 partially_masked_wfss_spectrum):
        importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)
        # This does not have a spectral axis mask so it should return as is
        result = importer_obj.apply_spectral_mask(make_empty_spectrum)
        assert result is make_empty_spectrum

        # This doesn't necessarily test something in the spectrum_list code,
        # but it's an error that we should be aware of.
        with pytest.raises(ValueError,
                           match='Spectral axis must be strictly increasing or decreasing.'):
            unmasked_spectrum.spectral_axis.mask[:] = True
            _ = importer_obj.apply_spectral_mask(unmasked_spectrum)

        spec = partially_masked_wfss_spectrum
        mask = spec.spectral_axis.mask
        result = importer_obj.apply_spectral_mask(spec)
        assert np.all(result.flux == spec.flux[~mask])
        assert np.all(result.spectral_axis == spec.spectral_axis[~mask])
        assert np.all(result.uncertainty.array == spec.uncertainty[~mask].array)
        assert np.all(result.mask == mask[~mask])

    def test_combine_lists_to_1d_spectrum(self):
        wl = [1, 2, 3] * u.nm
        fnu = [10, 20, 30] * u.Jy
        dfnu = [4, 5, 6] * u.Jy
        spec = combine_lists_to_1d_spectrum(wl, fnu, dfnu, u.nm, u.Jy)
        assert isinstance(spec, Spectrum)
        assert isinstance(spec.flux, u.Quantity)
        assert isinstance(spec.spectral_axis, u.Quantity)
        assert isinstance(spec.uncertainty, StdDevUncertainty)
        assert np.all(spec.flux.value == np.array([10, 20, 30]))
        assert np.all(spec.spectral_axis.value == np.array([1, 2, 3]))
        assert np.all(spec.uncertainty.array == np.array([4, 5, 6]))

    def test_combine_lists_to_1d_spectrum_no_uncertainty(self):
        wl = [1, 2, 3] * u.nm
        fnu = [10, 20, 30] * u.Jy
        spec = combine_lists_to_1d_spectrum(wl, fnu, None, u.nm, u.Jy)
        assert spec.uncertainty is None

    def test_output(self, deconfigged_helper, spectrum_list):
        importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)
        # Must make a selection for output to work
        importer_obj.spectra.selected = '1D Spectrum at index: 0'
        assert isinstance(importer_obj.output, list)

        single_spectrum_dict = importer_obj.output[0]
        assert isinstance(single_spectrum_dict, dict)
        assert all(single_spectrum_dict['obj'].flux == spectrum_list[0].flux)
        assert all(single_spectrum_dict['obj'].spectral_axis == spectrum_list[0].spectral_axis)

        keys = {'label', 'name', 'ver', 'name_ver', 'index', '_suffix', 'obj'}
        assert keys.issubset(set(single_spectrum_dict.keys()))
        assert isinstance(single_spectrum_dict['obj'], Spectrum)

        # TODO: This triggers the strictly increasing/decreasing error
        # assert SpectrumList(single_spectrum_dict['obj']) == spectrum_list

    def test_default_viewer_reference(self, deconfigged_helper, spectrum_list):
        importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)
        assert importer_obj.default_viewer_reference == 'spectrum-1d-viewer'

    def test_call_method_basic(self, deconfigged_helper, spectrum_list):
        importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)
        importer_obj.input = spectrum_list
        spectra_selected = ['1D Spectrum at index: 0',
                            '1D Spectrum at index: 1',
                            'Exposure 0, Source ID: 1111',
                            'Exposure 0, Source ID: 1111']
        importer_obj.spectra.selected = spectra_selected
        importer_obj.__call__()

        assert importer_obj.previous_data_label_messages == []

        # Data collection items
        dc = deconfigged_helper.app.data_collection
        assert len(dc) == 4  # 4 spectra loaded

        labels = ['1D Spectrum_index-0',
                  '1D Spectrum_index-1',
                  '1D Spectrum_EXP-0_ID-1111',
                  '1D Spectrum_EXP-0_ID-1111 (1)']

        assert all([label in labels for label in dc.labels])

        # Viewer items
        viewers = deconfigged_helper.viewers
        assert len(viewers) == 1
        assert '1D Spectrum' in viewers

        viewer = viewers['1D Spectrum']
        viewer_dm = viewer.data_menu

        for v in (viewer, viewer_dm):
            # TODO: should this be the case?
            # Repeated label name gets overwritten
            assert len(v.data_labels_loaded) == 3
            assert all([label in labels for label in v.data_labels_loaded])
            assert len(v.data_labels_visible) == 3
            assert all([label in labels for label in v.data_labels_visible])

#
#
# def test_spectrum_list_concatenated_importer_init(deconfigged_helper):
#     importer = SpectrumListConcatenatedImporter(app=deconfigged_helper)
#     assert hasattr(importer, 'output')
#     # output property should not fail if spectra is not set
#     try:
#         _ = importer.output
#     except Exception:
#         pass
#
#
# def test_spectrum_list_importer_methods(deconfigged_helper):
#     importer = SpectrumListImporter(app=deconfigged_helper)
#     # Call some methods if available for coverage
#     if hasattr(importer, 'is_valid'):
#         assert isinstance(importer.is_valid, bool) or callable(importer.is_valid)
#     if hasattr(importer, 'use_spectra_component'):
#         assert isinstance(importer.use_spectra_component, bool)
