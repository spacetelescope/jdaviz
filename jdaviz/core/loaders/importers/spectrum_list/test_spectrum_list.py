import numpy as np
import pytest
from astropy import units as u
from astropy.nddata import StdDevUncertainty
from specutils import Spectrum, SpectrumList, SpectrumCollection
from jdaviz.core.loaders.importers.spectrum_list.spectrum_list import (
    SpectrumListImporter,
    SpectrumListConcatenatedImporter,
    combine_lists_to_1d_spectrum
)


def make_spectrum(mask, wfss = False, collection = False):
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


class TestSpectrumListImporter:

    # def __init__(self):
    #     pass

    # TODO: make sure nothing is messed up with mutability
    spectrum_list = SpectrumList([unmasked_spectrum, masked_spectrum,
                                  wfss_spectrum, partially_masked_wfss_spectrum,
                                  fully_masked_wfss_spectrum])

    def test_is_valid(self, deconfigged_helper, spectrum_list,
                      unmasked_spectrum, unmasked_2d_spectrum):
        ldr = deconfigged_helper.loaders['object']
        ldr.object = spectrum_list
        assert ldr.is_valid

        ldr.object = unmasked_spectrum
        assert not ldr.is_valid

        ldr.object = unmasked_2d_spectrum
        assert ldr.is_valid

        ldr.object = make_spectrum(mask=False, collection=True)
        assert ldr.is_valid

# TODO: May have to do dummy class as in template_mixin tests
    @pytest.mark.parametrize('spec', spectrum_list)
    def test_input_to_list_of_spec_1d(self, deconfigged_helper, spec):
        importer = SpectrumListImporter(app=deconfigged_helper)
        out = importer.input_to_list_of_spec(spec)
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
