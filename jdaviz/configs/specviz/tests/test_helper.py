import pytest
from astropy import units as u
from astropy.tests.helper import assert_quantity_allclose
from glue.core.roi import XRangeROI
from specutils import Spectrum1D, SpectrumList, SpectrumCollection

from jdaviz.configs.specviz.plugins.unit_conversion import unit_conversion as uc


class TestSpecvizHelper:
    @pytest.fixture(autouse=True)
    def setup_class(self, specviz_app, spectrum1d):
        self.spec_app = specviz_app
        self.spec = spectrum1d
        self.spec_list = SpectrumList([spectrum1d] * 3)

        self.label = "Test 1D Spectrum"
        self.spec_app.load_spectrum(spectrum1d, data_label=self.label)

    def test_load_spectrum1d(self):
        assert len(self.spec_app.app.data_collection) == 1
        assert self.spec_app.app.data_collection[0].label == self.label

        data = self.spec_app.app.get_data_from_viewer('spectrum-viewer')

        assert isinstance(list(data.values())[0], Spectrum1D)
        assert list(data.keys())[0] == self.label

    def test_load_spectrum_list_no_labels(self):
        self.spec_app.load_spectrum(self.spec_list)
        assert len(self.spec_app.app.data_collection) == 4
        for i in (1, 2, 3):
            assert "specviz_data" in self.spec_app.app.data_collection[i].label

    def test_load_spectrum_list_with_labels(self):
        labels = ["List test 1", "List test 2", "List test 3"]
        self.spec_app.load_spectrum(self.spec_list, data_label=labels)
        assert len(self.spec_app.app.data_collection) == 4

    def test_mismatched_label_length(self):
        with pytest.raises(ValueError, match='Length'):
            labels = ["List test 1", "List test 2"]
            self.spec_app.load_spectrum(self.spec_list, data_label=labels)

    def test_load_spectrum_collection(self):
        with pytest.raises(TypeError):
            collection = SpectrumCollection([1]*u.AA)
            self.spec_app.load_spectrum(collection)

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


def test_get_spectral_regions_unit(specviz_app, spectrum1d):
    # Ensure units we put in are the same as the units we get out
    specviz_app.load_spectrum(spectrum1d)
    specviz_app.app.get_viewer("spectrum-viewer").apply_roi(XRangeROI(1, 3.5))

    subsets = specviz_app.get_spectral_regions()
    reg = subsets.get('Subset 1')

    assert spectrum1d.wavelength.unit == reg.lower.unit
    assert spectrum1d.wavelength.unit == reg.upper.unit


def test_get_spectral_regions_unit_conversion(specviz_app, spectrum1d):
    # If the reference (visible) data changes via unit conversion,
    # check that the region's units convert too
    specviz_app.load_spectrum(spectrum1d)
    specviz_app.app.get_viewer("spectrum-viewer").apply_roi(XRangeROI(1, 3.5))

    # Convert the wavelength axis to microns
    new_spectral_axis = "micron"
    conv_func = uc.UnitConversion.process_unit_conversion
    converted_spectrum = conv_func(specviz_app.app, spectrum=spectrum1d,
                                   new_spectral_axis=new_spectral_axis)

    # Add this new data and clear the other, making the converted spectrum our reference
    specviz_app.app.add_data(converted_spectrum, "Converted Spectrum")
    specviz_app.app.add_data_to_viewer("spectrum-viewer",
                                       "Converted Spectrum",
                                       clear_other_data=True)

    # Retrieve the Subset
    subsets = specviz_app.get_spectral_regions()
    reg = subsets.get('Subset 1')

    assert reg.lower.unit == u.Unit(new_spectral_axis)
    assert reg.upper.unit == u.Unit(new_spectral_axis)
