import astropy.units as u
import numpy as np
import pytest
from jdaviz.configs.specviz.helper import SpecViz
from specutils import Spectrum1D, SpectrumCollection


@pytest.fixture
def specviz_app():
    return SpecViz()


@pytest.fixture
def spectrum1d():
    spec_axis = np.linspace(6000, 8000, 1024) * u.AA
    flux = (np.random.randn(len(spec_axis.value)) +
            10*np.exp(-0.001*(spec_axis.value-6563)**2) +
            spec_axis.value/500) * u.Jy

    return Spectrum1D(spectral_axis=spec_axis, flux=flux)


@pytest.fixture
def spectrum_collection(spectrum1d):
    sc = [spectrum1d for _ in range(5)]

    return SpectrumCollection.from_spectra(sc)


def test_load_spectrum1d(specviz_app, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_app.load_spectrum(spectrum1d, data_label=label)

    assert len(specviz_app.app.data_collection) == 1
    assert specviz_app.app.data_collection[0].label == label

    data = specviz_app.app.get_data_from_viewer('spectrum-viewer')

    assert isinstance(list(data.values())[0], Spectrum1D)
    assert list(data.keys())[0] == label


# 1 3 5 6 7 8 9 11
def test_get_spectra(specviz_app, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_app.load_spectrum(spectrum1d, data_label=label)

    spectra = specviz_app.get_spectra()

    assert np.allclose(spectra[label].flux, spectrum1d.flux)
    assert spectra[label].flux.unit == spectrum1d.flux.unit


# 1 2
def test_get_spectra_no_redshift(specviz_app, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_app.load_spectrum(spectrum1d, data_label=label)

    spectra = specviz_app.get_spectra(apply_slider_redshift=None)

    assert np.allclose(spectra[label].flux, spectrum1d.flux)
    assert spectra[label].flux.unit == spectrum1d.flux.unit


# 1 3 5 6 7 9 11
def test_get_spectra_no_data_label(specviz_app, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_app.load_spectrum(spectrum1d, data_label=label)

    spectra = specviz_app.get_spectra(data_label=None, apply_slider_redshift="Error")

    assert np.allclose(spectra[label].flux, spectrum1d.flux)
    assert spectra[label].flux.unit == spectrum1d.flux.unit


# 1 3 5 6 7 8 9 11 DUPLICATE
def test_get_spectra_no_label_redshift_warn(specviz_app, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_app.load_spectrum(spectrum1d, data_label=label)

    spectra = specviz_app.get_spectra(data_label=None, apply_slider_redshift="Warn")

    assert np.allclose(spectra[label].flux, spectrum1d.flux)
    assert spectra[label].flux.unit == spectrum1d.flux.unit


# 1 3 4 5 6 7 9 10 11
def test_get_spectra_label_redshift(specviz_app, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_app.load_spectrum(spectrum1d, data_label=label)

    spectra = specviz_app.get_spectra(data_label=label, apply_slider_redshift="Error")

    assert np.allclose(spectra.flux, spectrum1d.flux)
    assert spectra.flux.unit == spectrum1d.flux.unit


# 1 3 4 5 6 7 8 9 10 11
def test_get_spectra_label_redshift_warn(specviz_app, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_app.load_spectrum(spectrum1d, data_label=label)

    spectra = specviz_app.get_spectra(data_label=label, apply_slider_redshift="Warn")

    assert np.allclose(spectra.flux, spectrum1d.flux)
    assert spectra.flux.unit == spectrum1d.flux.unit


# 1 3 5 7 8 9 11
def test_get_spectra_no_spectra(specviz_app, spectrum1d):
    spectra = specviz_app.get_spectra()

    assert spectra == {}


# 1 3 5 7 9 11
def test_get_spectra_no_spectra_redshift_error(specviz_app, spectrum1d):
    spectra = specviz_app.get_spectra(apply_slider_redshift="Error")

    assert spectra == {}


# 1 3 4 5 7 8 9 10 11
def test_get_spectra_no_spectra_label(specviz_app, spectrum1d):
    label = "label"
    with pytest.raises(AttributeError):
        spectra = specviz_app.get_spectra(data_label=label)


# 1 3 4 5 7 9 10 11
def test_get_spectra_no_spectra_label_redshift_error(specviz_app, spectrum1d):
    label = "label"
    with pytest.raises(AttributeError):
        spectra = specviz_app.get_spectra(data_label=label, apply_slider_redshift="Error")
