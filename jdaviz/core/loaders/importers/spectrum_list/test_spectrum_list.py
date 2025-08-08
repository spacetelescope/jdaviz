import numpy as np
import pytest
from astropy import units as u
from specutils import Spectrum, SpectrumList, SpectrumCollection

from jdaviz.core.loaders.importers.spectrum_list.spectrum_list import (
    SpectrumListImporter,
    # combine_lists_to_1d_spectrum
)

from jdaviz.core.registries import loader_importer_registry


def make_spectrum(mask, wfss=False, collection=False):
    cls = Spectrum
    flux = np.arange(5) * u.Jy
    spectral_axis = np.arange(5) * u.nm
    meta = {}

    if isinstance(mask, bool):
        mask = np.array([mask] * 5)

    if wfss:
        meta = {'header': {'DATAMODL': 'WFSSMulti', 'EXPGRPID': '0_0_0_1'}, 'source_id': '1111'}

    if collection:
        cls = SpectrumCollection

    return cls(flux=flux, spectral_axis=spectral_axis, mask=mask, meta=meta)


@pytest.fixture
def unmasked_spectrum():
    return make_spectrum(mask=False)


@pytest.fixture
def masked_spectrum():
    return make_spectrum(mask=True)


@pytest.fixture
def wfss_spectrum():
    return make_spectrum(mask=False, wfss=True)


# WFSS may have spectral axes that are partially masked
# and this is not allowed in specutils
@pytest.fixture
def partially_masked_wfss_spectrum():
    return make_spectrum(mask=np.array([False, True, False, True, False]), wfss=True)


@pytest.fixture
def fully_masked_wfss_spectrum():
    return make_spectrum(mask=True, wfss=True)


@pytest.fixture
def unmasked_2d_spectrum():
    flux = np.ones((2, 5)) * u.Jy
    spectral_axis = np.arange(5) * u.nm
    return Spectrum(flux=flux, spectral_axis=spectral_axis)


@pytest.fixture
def spectrum_list(unmasked_spectrum, masked_spectrum, wfss_spectrum,
                  partially_masked_wfss_spectrum, fully_masked_wfss_spectrum):
    return SpectrumList([
        unmasked_spectrum,
        masked_spectrum,
        wfss_spectrum,
        partially_masked_wfss_spectrum,
        fully_masked_wfss_spectrum])


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

    def test_is_valid(self, deconfigged_helper, spectrum_list,
                      unmasked_spectrum, unmasked_2d_spectrum):
        importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)
        assert importer_obj.is_valid

        importer_obj.input = unmasked_spectrum
        assert not importer_obj.is_valid

        importer_obj.input = unmasked_2d_spectrum
        assert importer_obj.is_valid

        importer_obj.input = make_spectrum(mask=False, wfss=False)
        assert not importer_obj.is_valid

        importer_obj.input = make_spectrum(mask=False, collection=True)
        assert importer_obj.is_valid

    def test_input_to_list_of_spec_1d(self, deconfigged_helper, spectrum_list):
        importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)

        for spec in spectrum_list:
            out = importer_obj.input_to_list_of_spec(spec)
            assert isinstance(out, list)
            out = out[0]
            assert isinstance(out, Spectrum)

            spectral_axis = spec.spectral_axis
            if hasattr(spectral_axis, 'mask'):
                mask = spectral_axis.mask
                assert np.all(out.flux == spec.flux[mask])
                assert np.all(out.spectral_axis == spectral_axis[mask])
                assert np.all(out.uncertainty == spec.uncertainty[mask])
                assert np.all(out.mask == mask[mask])

    # def test_input_to_list_of_spec_1d_masked(self, deconfigged_helper, spectrum_list):
    #     importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)
    #     partially_masked_wfss_spectrum = spectrum_list[3]
    #     out = importer_obj.input_to_list_of_spec(partially_masked_wfss_spectrum)
    #     assert isinstance(out, list)
    #     assert isinstance(out[0], Spectrum)
    #
    # def test_input_to_list_of_spec_2d(self, deconfigged_helper, spectrum_list):
    #     importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)
    #     flux = np.ones((2, 5)) * u.Jy
    #     spectral_axis = np.arange(5) * u.nm
    #     spec = Spectrum(flux=flux, spectral_axis=spectral_axis)
    #     out = importer_obj.input_to_list_of_spec(spec)
    #     assert isinstance(out, list)
    #     assert len(out) == 2
    #
    # def test_input_to_list_of_spec_collection(self, deconfigged_helper, spectrum_list):
    #     importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)
    #     spec1 = spectrum_list[0]
    #     spec2 = spectrum_list[1]
    #     inp = SpectrumCollection([spec1, spec2])
    #     out = importer_obj.input_to_list_of_spec(inp)
    #     assert all(isinstance(s, Spectrum) for s in out)
    #
    # def test_input_to_list_of_spec_not_supported(self, deconfigged_helper, spectrum_list):
    #     importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)
    #     with pytest.raises(NotImplementedError):
    #         importer_obj.input_to_list_of_spec('not_a_spectrum')
    #
    # def test_is_wfssmulti_and_labels(self, deconfigged_helper, spectrum_list):
    #     importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)
    #     spec = spectrum_list[2]  # wfss_spectrum
    #     assert importer_obj.is_wfssmulti(spec)
    #     expid, label, suffix = importer_obj.generate_wfssmulti_labels(spec)
    #     assert 'Exposure' in label
    #     assert 'EXP-' in suffix
    #
    # def test_has_mask_and_is_fully_masked(self, deconfigged_helper, spectrum_list):
    #     importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)
    #     spec = spectrum_list[1]  # masked_spectrum
    #     assert importer_obj.has_mask(spec)
    #     assert importer_obj.is_fully_masked(spec)
    #     spec2 = spectrum_list[0]  # unmasked_spectrum
    #     assert not importer_obj.is_fully_masked(spec2)
    #
    # def test_apply_spectral_mask(self, deconfigged_helper, spectrum_list):
    #     importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)
    #     spec = spectrum_list[0]  # unmasked_spectrum
    #     out = importer_obj.apply_spectral_mask(spec)
    #     assert isinstance(out, Spectrum)
    #
    # def test_default_viewer_reference(self, deconfigged_helper, spectrum_list):
    #     importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)
    #     spec = spectrum_list[0]
    #     importer_obj.input = SpectrumList([spec])
    #     importer_obj.spectra = type('Spectra', (),
    #     {'selected_obj_dict': [{'obj': spec, 'suffix': 'index-0'}]})()
    #     importer_obj.data_label_value = 'testlabel'
    #     importer_obj.__call__()
    #
    # def test_call_method(self, deconfigged_helper, spectrum_list):
    #     importer_obj = self.setup_importer_obj(deconfigged_helper, spectrum_list)
    #     spec = spectrum_list[0]
    #     importer_obj.input = SpectrumList([spec])
    #     importer_obj.spectra = type('Spectra', (),
    #     {'selected_obj_dict': [{'obj': spec, 'suffix': 'index-0'}]})()
    #     importer_obj.data_label_value = 'testlabel'
    #     importer_obj.__call__()
    #
    # def test_combine_lists_to_1d_spectrum(self):
    #     wl = [1, 2, 3] * u.nm
    #     fnu = [10, 20, 30] * u.Jy
    #     dfnu = [1, 2, 3] * u.Jy
    #     spec = combine_lists_to_1d_spectrum(wl, fnu, dfnu, u.nm, u.Jy)
    #     assert isinstance(spec, Spectrum)
    #     assert np.all(spec.flux.value == np.array([10, 20, 30]))
    #
    # def test_combine_lists_to_1d_spectrum_no_uncertainty(self):
    #     wl = [1, 2, 3] * u.nm
    #     fnu = [10, 20, 30] * u.Jy
    #     spec = combine_lists_to_1d_spectrum(wl, fnu, None, u.nm, u.Jy)
    #     assert isinstance(spec, Spectrum)
    #     assert spec.uncertainty is None
    #
    # def test_spectrum_list_importer_init(self, deconfigged_helper):
    #     importer = SpectrumListImporter(app=deconfigged_helper.app)
    #     assert importer.data_label_default == '1D Spectrum'
    #     assert hasattr(importer, 'spectra_items')
    #     assert hasattr(importer, 'spectra_selected')
    #     assert hasattr(importer, 'spectra_multiselect')
    #     assert hasattr(importer, 'disable_dropdown')
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
