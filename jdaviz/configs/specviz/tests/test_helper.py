import numpy as np
import pytest

from specutils import Spectrum1D


def test_load_spectrum1d(specviz_app, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_app.load_spectrum(spectrum1d, data_label=label)

    assert len(specviz_app.app.data_collection) == 1
    assert specviz_app.app.data_collection[0].label == label

    data = specviz_app.app.get_data_from_viewer('spectrum-viewer')

    assert isinstance(list(data.values())[0], Spectrum1D)
    assert list(data.keys())[0] == label


def test_get_spectra(specviz_app, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_app.load_spectrum(spectrum1d, data_label=label)

    spectra = specviz_app.get_spectra()

    assert np.allclose(spectra[label].flux, spectrum1d.flux)
    assert spectra[label].flux.unit == spectrum1d.flux.unit


def test_get_spectra_no_redshift(specviz_app, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_app.load_spectrum(spectrum1d, data_label=label)

    spectra = specviz_app.get_spectra(apply_slider_redshift=None)

    assert np.allclose(spectra[label].flux, spectrum1d.flux)
    assert spectra[label].flux.unit == spectrum1d.flux.unit


def test_get_spectra_no_data_label(specviz_app, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_app.load_spectrum(spectrum1d, data_label=label)

    spectra = specviz_app.get_spectra(data_label=None, apply_slider_redshift="Error")

    assert np.allclose(spectra[label].flux, spectrum1d.flux)
    assert spectra[label].flux.unit == spectrum1d.flux.unit


def test_get_spectra_label_redshift(specviz_app, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_app.load_spectrum(spectrum1d, data_label=label)

    spectra = specviz_app.get_spectra(data_label=label, apply_slider_redshift="Error")

    assert np.allclose(spectra.flux, spectrum1d.flux)
    assert spectra.flux.unit == spectrum1d.flux.unit


def test_get_spectra_label_redshift_warn(specviz_app, spectrum1d):
    label = "Test 1D Spectrum"
    specviz_app.load_spectrum(spectrum1d, data_label=label)

    spectra = specviz_app.get_spectra(data_label=label, apply_slider_redshift="Warn")

    assert np.allclose(spectra.flux, spectrum1d.flux)
    assert spectra.flux.unit == spectrum1d.flux.unit


def test_get_spectra_no_spectra(specviz_app, spectrum1d):
    spectra = specviz_app.get_spectra()

    assert spectra == {}


def test_get_spectra_no_spectra_redshift_error(specviz_app, spectrum1d):
    spectra = specviz_app.get_spectra(apply_slider_redshift="Error")

    assert spectra == {}


def test_get_spectra_no_spectra_label(specviz_app, spectrum1d):
    label = "label"
    with pytest.raises(AttributeError):
        specviz_app.get_spectra(data_label=label)


def test_get_spectra_no_spectra_label_redshift_error(specviz_app, spectrum1d):
    label = "label"
    with pytest.raises(AttributeError):
        specviz_app.get_spectra(data_label=label, apply_slider_redshift="Error")
