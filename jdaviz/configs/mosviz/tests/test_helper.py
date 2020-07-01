import pytest
from specutils import Spectrum1D, SpectrumCollection
import numpy as np
import astropy.units as u

from ..helper import MosViz


@pytest.fixture
def mosviz_app():
    return MosViz()


@pytest.fixture
def spectrum1d():
    spec_axis = np.linspace(6000, 8000, 1024) * u.AA
    flux = (np.random.randn(len(spec_axis.value)) +
            10*np.exp(-0.001*(spec_axis.value-6563)**2) +
            spec_axis.value/500) * u.Jy

    return Spectrum1D(spectral_axis=spec_axis, flux=flux)


@pytest.fixture
def spectrum2d():
    pass


@pytest.fixture
def spectrum_collection(spectrum1d):
    sc = [spectrum1d for _ in range(5)]

    return SpectrumCollection.from_spectra(sc)


def test_load_spectrum1d(mosviz_app, spectrum1d):
    label = "Test 1D Spectrum"
    mosviz_app.load_1d_spectra(spectrum1d, data_labels=label)

    assert len(mosviz_app.app.data_collection) == 1
    assert mosviz_app.app.data_collection[0].label == label

    data = mosviz_app.app.get_data_from_viewer('spectrum-viewer')

    assert isinstance(list(data.values())[0], Spectrum1D)
    assert list(data.keys())[0] == label

    with pytest.raises(ValueError) as e:
        mosviz_app.load_1d_spectra([1, 2, 3])


def test_load_spectrum_collection(mosviz_app, spectrum_collection):
    labels = [f"Test Spectrum Collection {i}" for i in range(5)]
    mosviz_app.load_1d_spectra(spectrum_collection, data_labels=labels)

    assert len(mosviz_app.app.data_collection) == 5
    assert mosviz_app.app.data_collection[0].label == labels[0]

    # Test to see if the last spectrum object in the collection was
    #  successfully added to the viewer
    data = mosviz_app.app.get_data_from_viewer('spectrum-viewer')

    assert isinstance(list(data.values())[0], Spectrum1D)
    assert list(data.keys())[0] == labels[-1]

    with pytest.raises(ValueError) as e:
        mosviz_app.load_1d_spectra([1, 2, 3])


