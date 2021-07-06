import pytest
from astropy import units as u
from astropy.tests.helper import assert_quantity_allclose

from specutils import Spectrum1D


class TestSpecvizHelper:
    @pytest.fixture(autouse=True)
    def setup_class(self, specviz_app, spectrum1d):
        self.spec_app = specviz_app
        self.spec = spectrum1d

        self.label = "Test 1D Spectrum"
        self.spec_app.load_spectrum(spectrum1d, data_label=self.label)

    def test_load_spectrum1d(self):
        assert len(self.spec_app.app.data_collection) == 1
        assert self.spec_app.app.data_collection[0].label == self.label

        data = self.spec_app.app.get_data_from_viewer('spectrum-viewer')

        assert isinstance(list(data.values())[0], Spectrum1D)
        assert list(data.keys())[0] == self.label

    def test_get_spectra(self):
        spectra = self.spec_app.get_spectra()

        assert_quantity_allclose(spectra[self.label].flux,
                                 self.spec.flux, atol=1e-5*u.Unit(self.spec.flux.unit))

    def test_get_spectra_no_redshift(self):
        spectra = self.spec_app.get_spectra(apply_slider_redshift=None)

        assert_quantity_allclose(spectra[self.label].flux,
                                 self.spec.flux, atol=1e-5*u.Unit(self.spec.flux.unit))

    def test_get_spectra_no_data_label(self):
        spectra = self.spec_app.get_spectra(data_label=None, apply_slider_redshift=True)

        assert_quantity_allclose(spectra[self.label].flux,
                                 self.spec.flux, atol=1e-5*u.Unit(self.spec.flux.unit))

    def test_get_spectra_label_redshift(self):
        spectra = self.spec_app.get_spectra(data_label=self.label, apply_slider_redshift=True)

        assert_quantity_allclose(spectra.flux,
                                 self.spec.flux, atol=1e-5*u.Unit(self.spec.flux.unit))

    def test_get_spectra_label_redshift_warn(self):
        spectra = self.spec_app.get_spectra(data_label=self.label, apply_slider_redshift="Warn")

        assert_quantity_allclose(spectra.flux,
                                 self.spec.flux, atol=1e-5*u.Unit(self.spec.flux.unit))


def test_get_spectra_no_spectra(specviz_app, spectrum1d):
    spectra = specviz_app.get_spectra()

    assert spectra == {}


def test_get_spectra_no_spectra_redshift_error(specviz_app, spectrum1d):
    spectra = specviz_app.get_spectra(apply_slider_redshift=True)

    assert spectra == {}


def test_get_spectra_no_spectra_label(specviz_app, spectrum1d):
    label = "label"
    with pytest.raises(AttributeError):
        specviz_app.get_spectra(data_label=label)


def test_get_spectra_no_spectra_label_redshift_error(specviz_app, spectrum1d):
    label = "label"
    with pytest.raises(AttributeError):
        specviz_app.get_spectra(data_label=label, apply_slider_redshift=True)
