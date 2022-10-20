from zipfile import ZipFile
from packaging.version import Version

import specutils
import pytest
from astropy import units as u
from astropy.tests.helper import assert_quantity_allclose
from glue.core.roi import XRangeROI
from glue.core.edit_subset_mode import OrMode
from specutils import Spectrum1D, SpectrumList, SpectrumCollection
from astropy.utils.data import download_file

from jdaviz.app import Application
from jdaviz.configs.specviz.plugins.unit_conversion import unit_conversion as uc
from jdaviz.core.marks import LineUncertainties
from jdaviz import Specviz


class TestSpecvizHelper:
    @pytest.fixture(autouse=True)
    def setup_class(self, specviz_helper, spectrum1d):
        self.spec_app = specviz_helper
        self.spec = spectrum1d
        self.spec_list = SpectrumList([spectrum1d] * 3)

        self.label = "Test 1D Spectrum"
        self.spec_app.load_spectrum(spectrum1d, data_label=self.label)

    def test_load_spectrum1d(self):
        assert len(self.spec_app.app.data_collection) == 1
        dc_0 = self.spec_app.app.data_collection[0]
        assert dc_0.label == self.label
        assert dc_0.meta['uncertainty_type'] == 'std'

        data = self.spec_app.app.get_data_from_viewer('spectrum-viewer')

        assert isinstance(list(data.values())[0], Spectrum1D)
        assert list(data.keys())[0] == self.label

    def test_load_spectrum_list_no_labels(self):
        self.spec_app.load_spectrum(self.spec_list)
        assert len(self.spec_app.app.data_collection) == 5
        for i in (1, 2, 3):
            assert "specviz_data" in self.spec_app.app.data_collection[i].label

    def test_load_spectrum_list_with_labels(self):
        labels = ["List test 1", "List test 2", "List test 3"]
        self.spec_app.load_spectrum(self.spec_list, data_label=labels)
        assert len(self.spec_app.app.data_collection) == 5

    def test_mismatched_label_length(self):
        with pytest.raises(ValueError, match='Length'):
            labels = ["List test 1", "List test 2"]
            self.spec_app.load_spectrum(self.spec_list, data_label=labels)

    def test_load_spectrum_collection(self):
        with pytest.raises(TypeError):
            collection = SpectrumCollection([1]*u.AA)
            self.spec_app.load_spectrum(collection)

    def test_get_spectra(self):
        with pytest.warns(UserWarning, match='Applying the value from the redshift slider'):
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
        with pytest.warns(UserWarning, match='Applying the value from the redshift slider'):
            spectra = self.spec_app.get_spectra(data_label=self.label, apply_slider_redshift="Warn")

        assert_quantity_allclose(spectra.flux,
                                 self.spec.flux, atol=1e-5*u.Unit(self.spec.flux.unit))

    def test_get_spectral_regions_none(self):
        spec_region = self.spec_app.get_spectral_regions()

        assert spec_region == {}

    def test_get_spectral_regions_one(self):
        self.spec_app.app.get_viewer("spectrum-viewer").apply_roi(XRangeROI(6000, 6500))
        spec_region = self.spec_app.get_spectral_regions()
        assert len(spec_region['Subset 1'].subregions) == 1

    def test_get_spectral_regions_two(self):
        spectrum_viewer = self.spec_app.app.get_viewer("spectrum-viewer")

        # Set the active edit_subset_mode to OrMode to be able to add multiple subregions
        spectrum_viewer.session.edit_subset_mode._mode = OrMode
        self.spec_app.app.get_viewer("spectrum-viewer").apply_roi(XRangeROI(6000, 6500))
        self.spec_app.app.get_viewer("spectrum-viewer").apply_roi(XRangeROI(7300, 7800))

        spec_region = self.spec_app.get_spectral_regions()

        assert len(spec_region['Subset 1'].subregions) == 2

    def test_get_spectral_regions_three(self):
        spectrum_viewer = self.spec_app.app.get_viewer("spectrum-viewer")

        spectrum_viewer.session.edit_subset_mode._mode = OrMode
        self.spec_app.app.get_viewer("spectrum-viewer").apply_roi(XRangeROI(6000, 6400))
        self.spec_app.app.get_viewer("spectrum-viewer").apply_roi(XRangeROI(6600, 7000))
        self.spec_app.app.get_viewer("spectrum-viewer").apply_roi(XRangeROI(7300, 7800))

        spec_region = self.spec_app.get_spectral_regions()

        assert len(spec_region['Subset 1'].subregions) == 3
        # Assert correct values for test with 3 subregions
        assert_quantity_allclose(spec_region['Subset 1'].subregions[0][0].value,
                                 6000., atol=1e-5)
        assert_quantity_allclose(spec_region['Subset 1'].subregions[0][1].value,
                                 6222.22222222, atol=1e-5)

        assert_quantity_allclose(spec_region['Subset 1'].subregions[1][0].value,
                                 6666.66666667, atol=1e-5)
        assert_quantity_allclose(spec_region['Subset 1'].subregions[1][1].value,
                                 6888.88888889, atol=1e-5)

        assert_quantity_allclose(spec_region['Subset 1'].subregions[2][0].value,
                                 7333.33333333, atol=1e-5)
        assert_quantity_allclose(spec_region['Subset 1'].subregions[2][1].value,
                                 7777.77777778, atol=1e-5)

    def test_get_spectral_regions_raise_value_error(self):
        with pytest.raises(ValueError):
            spectrum_viewer = self.spec_app.app.get_viewer("spectrum-viewer")

            spectrum_viewer.session.edit_subset_mode._mode = OrMode
            # Selecting ROIs that are not part of the actual spectrum raises an error
            self.spec_app.app.get_viewer("spectrum-viewer").apply_roi(XRangeROI(1, 3))
            self.spec_app.app.get_viewer("spectrum-viewer").apply_roi(XRangeROI(4, 6))

            self.spec_app.get_spectral_regions()


def test_get_spectra_no_spectra(specviz_helper, spectrum1d):
    with pytest.warns(UserWarning, match='Applying the value from the redshift slider'):
        spectra = specviz_helper.get_spectra()

    assert spectra == {}


def test_get_spectra_no_spectra_redshift_error(specviz_helper, spectrum1d):
    spectra = specviz_helper.get_spectra(apply_slider_redshift=True)

    assert spectra == {}


def test_get_spectra_no_spectra_label(specviz_helper, spectrum1d):
    label = "label"
    with pytest.raises(AttributeError):
        specviz_helper.get_spectra(data_label=label)


def test_get_spectra_no_spectra_label_redshift_error(specviz_helper, spectrum1d):
    label = "label"
    with pytest.raises(AttributeError):
        specviz_helper.get_spectra(data_label=label, apply_slider_redshift=True)


def test_add_spectrum_after_subset(specviz_helper, spectrum1d):
    specviz_helper.load_spectrum(spectrum1d, data_label="test")
    specviz_helper.app.get_viewer("spectrum-viewer").apply_roi(XRangeROI(6200, 7000))
    new_spec = specviz_helper.get_spectra(apply_slider_redshift=True)["test"]*0.9
    specviz_helper.load_spectrum(new_spec, data_label="test2")


def test_get_spectral_regions_unit(specviz_helper, spectrum1d):
    # Ensure units we put in are the same as the units we get out
    specviz_helper.load_spectrum(spectrum1d)
    specviz_helper.app.get_viewer("spectrum-viewer").apply_roi(XRangeROI(6200, 7000))

    subsets = specviz_helper.get_spectral_regions()
    reg = subsets.get('Subset 1')

    assert spectrum1d.wavelength.unit == reg.lower.unit
    assert spectrum1d.wavelength.unit == reg.upper.unit


def test_get_spectral_regions_unit_conversion(specviz_helper, spectrum1d):
    # If the reference (visible) data changes via unit conversion,
    # check that the region's units convert too
    specviz_helper.load_spectrum(spectrum1d)

    # Also check coordinates info panel
    spec_viewer = specviz_helper.app.get_viewer('spectrum-viewer')
    spec_viewer.on_mouse_or_key_event({'event': 'mousemove', 'domain': {'x': 6100, 'y': 12.5}})
    assert spec_viewer.label_mouseover.pixel == 'x=+6.10000e+03 y=+1.25000e+01'

    # Convert the wavelength axis to microns
    new_spectral_axis = "micron"
    conv_func = uc.UnitConversion.process_unit_conversion
    converted_spectrum = conv_func(specviz_helper.app, spectrum=spectrum1d,
                                   new_spectral_axis=new_spectral_axis)

    # Add this new data and clear the other, making the converted spectrum our reference
    specviz_helper.app.add_data(converted_spectrum, "Converted Spectrum")
    specviz_helper.app.add_data_to_viewer("spectrum-viewer",
                                          "Converted Spectrum",
                                          clear_other_data=True)

    specviz_helper.app.get_viewer("spectrum-viewer").apply_roi(XRangeROI(0.6, 0.7))

    # Retrieve the Subset
    subsets = specviz_helper.get_spectral_regions()
    reg = subsets.get('Subset 1')

    assert reg.lower.unit == u.Unit(new_spectral_axis)
    assert reg.upper.unit == u.Unit(new_spectral_axis)

    # Coordinates info panel should show new unit
    spec_viewer.on_mouse_or_key_event({'event': 'mousemove', 'domain': {'x': 0.61, 'y': 12.5}})
    assert spec_viewer.label_mouseover.pixel == 'x=+6.10000e-01 y=+1.25000e+01'


def test_subset_default_thickness(specviz_helper, spectrum1d):
    specviz_helper.load_spectrum(spectrum1d)

    sv = specviz_helper.app.get_viewer('spectrum-viewer')
    sv.toolbar.active_tool = sv.toolbar.tools['bqplot:xrange']
    from glue.core.roi import XRangeROI
    sv.apply_roi(XRangeROI(2.5, 3.5))
    # _on_layers_update is not triggered within CI
    sv._on_layers_update()
    assert sv.state.layers[-1].linewidth == 3


def test_app_links(specviz_helper, spectrum1d):
    sv = specviz_helper.app.get_viewer('spectrum-viewer')
    assert isinstance(sv.jdaviz_app, Application)
    assert isinstance(sv.jdaviz_helper, Specviz)


@pytest.mark.remote_data
def test_load_spectrum_list_directory(tmpdir, specviz_helper):
    test_data = 'https://stsci.box.com/shared/static/l2azhcqd3tvzhybdlpx2j2qlutkaro3z.zip'
    fn = download_file(test_data, cache=True, timeout=30)
    with ZipFile(fn, 'r') as sample_data_zip:
        sample_data_zip.extractall(tmpdir.strpath)
    data_path = str(tmpdir.join('NIRISS_for_parser_p0171'))

    with pytest.warns(UserWarning, match='SRCTYPE is missing or UNKNOWN in JWST x1d loader'):
        specviz_helper.load_spectrum(data_path)
    # NOTE: the length was 3 before specutils 1.9 (https://github.com/astropy/specutils/pull/982)
    SPECUTILS_LT_1_9 = Version(specutils.__version__) < Version('1.9.0')
    expected_len = 40 if not SPECUTILS_LT_1_9 else 3
    assert len(specviz_helper.app.data_collection) == expected_len
    for data in specviz_helper.app.data_collection:
        assert data.main_components[:2] == ['flux', 'uncertainty']

    dc_0 = specviz_helper.app.data_collection[0]
    assert 'header' not in dc_0.meta
    assert dc_0.meta['SPORDER'] == 1


def test_plot_uncertainties(specviz_helper, spectrum1d):
    specviz_helper.load_spectrum(spectrum1d)

    specviz_viewer = specviz_helper.app.get_viewer("spectrum-viewer")

    assert len([m for m in specviz_viewer.figure.marks if isinstance(m, LineUncertainties)]) == 0

    specviz_viewer.state.show_uncertainty = True
    uncert_marks = [m for m in specviz_viewer.figure.marks if isinstance(m, LineUncertainties)]
    assert len(uncert_marks) == 1
    # mark has a lower and upper boundary, but each should have the same length as the spectrum
    assert len(uncert_marks[0].x[0]) == len(spectrum1d.flux)

    # enable as-steps and make sure doesn't crash (won't change the number of marks)
    specviz_viewer.state.layers[0].as_steps = True
    specviz_viewer._plot_uncertainties()
    uncert_marks = [m for m in specviz_viewer.figure.marks if isinstance(m, LineUncertainties)]
    assert len(uncert_marks) == 1
    # now the mark should have double the length as its drawn on the bin edges
    assert len(uncert_marks[0].x[0]) == len(spectrum1d.flux) * 2

    specviz_viewer.state.show_uncertainty = False

    assert len([m for m in specviz_viewer.figure.marks if isinstance(m, LineUncertainties)]) == 0


def test_plugin_user_apis(specviz_helper):
    for plugin_name, plugin_api in specviz_helper.plugins.items():
        plugin = plugin_api._obj
        for attr in plugin_api._expose:
            assert hasattr(plugin, attr)


def test_data_label_as_posarg(specviz_helper, spectrum1d):
    # Passing in data_label keyword as posarg.
    specviz_helper.load_spectrum(spectrum1d, 'my_spec')
    assert specviz_helper.app.data_collection[0].label == 'my_spec'
