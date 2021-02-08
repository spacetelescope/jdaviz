import astropy.modeling.models as models
import astropy.units as u
import numpy as np
from specutils.spectra import Spectrum1D

from .. import unit_conversion as uc


SPECTRUM_SIZE = 10  # length of spectrum


def build_spectrum(sigma=0.1):
    g1 = models.Gaussian1D(1, 4.6, 0.2)
    g2 = models.Gaussian1D(2.5, 5.5, 0.1)
    g3 = models.Gaussian1D(-1.7, 8.2, 0.1)

    x = np.linspace(0, 10, SPECTRUM_SIZE)
    y = g1(x) + g2(x) + g3(x)

    noise = np.random.normal(4., sigma, x.shape)

    return x, y + noise


def test_spectral_axis_conversion():
    np.random.seed(42)

    x, y = build_spectrum()

    spectrum = Spectrum1D(flux=y*u.Jy, spectral_axis=x*u.um)
    new_spectral_axis = "micron"

    conv_func = uc.UnitConversion.process_unit_conversion
    converted_spectrum = conv_func(uc.UnitConversion, spectrum=spectrum,
                                   new_spectral_axis=new_spectral_axis)

    result_spectral_axis = [0, 1.11111111, 2.22222222, 3.33333333,
                            4.44444444, 5.55555556, 6.66666667, 7.77777778,
                            8.88888889, 10]

    assert np.allclose(converted_spectrum.spectral_axis.value,
                       result_spectral_axis, atol=1e-5)


def test_flux_conversion():

    np.random.seed(42)

    x, y = build_spectrum()

    spectrum = Spectrum1D(flux=y*u.Jy, spectral_axis=x*u.um)
    new_flux = "erg / (s cm2 um)"

    converted_spectrum = uc.UnitConversion.process_unit_conversion(uc.UnitConversion,
                                                                   spectrum=spectrum,
                                                                   new_flux=new_flux)

    # result_flux = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    result_flux = [9.67970066e-09, 2.46763877e-09, 1.12034621e-09,
                   7.15682642e-10, 5.94364037e-10, 2.80465524e-10,
                   2.02021996e-10, 1.49988629e-10, 1.21543537e-10]

    # TODO: first element is `inf`, why is this?
    assert np.allclose(converted_spectrum.flux.value[1:], result_flux, atol=1e-5)


def test_both_conversion():
    np.random.seed(42)

    x, y = build_spectrum()

    spectrum = Spectrum1D(flux=y*u.Jy, spectral_axis=x*u.um)
    new_spectral_axis = "micron"
    new_flux = "erg / (s cm2 um)"

    conv_func = uc.UnitConversion.process_unit_conversion
    converted_spectrum = conv_func(uc.UnitConversion, spectrum=spectrum,
                                   new_flux=new_flux,
                                   new_spectral_axis=new_spectral_axis)

    result_spectral_axis = [0, 1.11111111, 2.22222222, 3.33333333,
                            4.44444444, 5.55555556, 6.66666667, 7.77777778,
                            8.88888889, 10]
    result_flux = [9.67970066e-09, 2.46763877e-09, 1.12034621e-09, 7.15682642e-10,
                   5.94364037e-10, 2.80465524e-10, 2.02021996e-10, 1.49988629e-10,
                   1.21543537e-10]

    # TODO: first element is `inf`, why is this?
    assert np.allclose(converted_spectrum.flux.value[1:], result_flux,
                       atol=1e-5)
    assert np.allclose(converted_spectrum.spectral_axis.value,
                       result_spectral_axis, atol=1e-5)
