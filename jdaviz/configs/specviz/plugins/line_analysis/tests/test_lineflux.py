from astropy.tests.helper import assert_quantity_allclose
import astropy.units as u
from glue.viewers.profile.state import FUNCTIONS as COLLAPSE_FUNCTIONS
import numpy as np
import pytest
from specutils import Spectrum1D

from jdaviz import Cubeviz

import warnings
warnings.filterwarnings('ignore')

# Maps input spectrum flux unit to expected line analysis flux unit
expected_lineflux_results = {
    u.Jy/u.sr: u.Unit('W/(m2*sr)'),
    u.Jy: u.Unit('W/m2'),
    u.Unit('W/m2/m')/u.sr: u.Unit('W/(m2*sr)'),
    u.Unit('W/m2/m'): u.Unit('W/m2')
}

test_cases = list(expected_lineflux_results.keys())


# Test cases for unit gaussian tests
def _gauss_with_unity_area(x, mean, sigma):
    ''' Gaussian function with area = 1 unit '''
    dx = x - mean
    n = 1/(sigma*np.sqrt(2*np.pi))
    g = n * np.exp(-dx**2/(2*sigma**2))
    return g


mn = 1.5
sig = 0.01

# 5 cases: replace fl_wave with fnu_freq, fnu_wave, flam_wave, flam_freq, or fl_wave
# to try the different cases here
unit_flux_gaussian_test_cases = []

# unit-flux gaussian in frequency space
freq = np.arange(1, 2, 0.001)*u.Hz
flux_freq = _gauss_with_unity_area(freq.value, mn, sig)*1.0E26*u.Jy
fnu_freq = Spectrum1D(spectral_axis=freq, flux=flux_freq)
unit_flux_gaussian_test_cases.append(fnu_freq)
fnu_wave = Spectrum1D(spectral_axis=fnu_freq.wavelength, flux=flux_freq)
unit_flux_gaussian_test_cases.append(fnu_wave)

# unit-flux gaussian in wavelength space
lam = np.arange(1, 2, 0.001)*u.m
flux_wave = _gauss_with_unity_area(lam.value, mn, sig)*1.0*u.W/u.m**2/u.m
flam_wave = Spectrum1D(spectral_axis=lam, flux=flux_wave)
unit_flux_gaussian_test_cases.append(flam_wave)
flam_freq = Spectrum1D(spectral_axis=flam_wave.frequency, flux=flux_wave)
unit_flux_gaussian_test_cases.append(flam_freq)


def _calculate_line_flux(viz_helper):
    '''
    Returns the line flux calculation by opening the Line Analysis Plugin
    Assumes the plugin hasn't been opened yet
    '''
    # Open the plugin and force the calculation
    viz_helper.app.state.drawer = True
    line_analysis_plugin = viz_helper.app.get_tray_item_from_name('specviz-line-analysis')
    line_analysis_plugin.keep_active = True

    # Retrieve Results
    for result in line_analysis_plugin.results:
        if result['function'] == 'Line Flux':
            return result


@pytest.mark.filterwarnings(r"ignore:.* contains multiple slashes")
@pytest.mark.filterwarnings(r"ignore:.* apply_slider_redshift")
@pytest.mark.parametrize('spectra_fluxunit', test_cases)
def test_cubeviz_collapse_fluxunits(spectrum1d_cube_custom_fluxunit, spectra_fluxunit):
    ''' Calculates line flux and checks the units for each collapse function '''
    data = spectrum1d_cube_custom_fluxunit(spectra_fluxunit)
    for function in COLLAPSE_FUNCTIONS:
        # Initialize Cubeviz with specific data and collapse function
        cubeviz_helper = Cubeviz()
        data_label = "Test Cube"
        cubeviz_helper.load_data(data, data_label=data_label)
        cubeviz_helper.app.get_viewer('spectrum-viewer').state.function = function

        lineflux_result = _calculate_line_flux(cubeviz_helper)
        autocollapsed_spectrum_unit = (cubeviz_helper.
                                       specviz.get_spectra()[f"{data_label}[FLUX]"].flux.unit)
        # Futureproofing: Eventually Cubeviz autocollapse will change the flux units of the
        # spectra depending on whether the spectrum was collapsed OVER SPAXELS or not. Only
        # do the assertion check if we KNOW what the expected lineflux results should be
        if autocollapsed_spectrum_unit in expected_lineflux_results.keys():
            assert u.Unit(lineflux_result['unit']) == expected_lineflux_results[spectra_fluxunit]


@pytest.mark.filterwarnings(r"ignore:.* contains multiple slashes")
@pytest.mark.parametrize('test_case', unit_flux_gaussian_test_cases)
def test_unit_gaussian(specviz_helper, test_case):
    '''
    Test an Area 1 Gaussian and ensure the result returns in W/m2
    Test provided by Patrick Ogle
    '''
    specviz_helper.load_data(test_case)

    lineflux_result = _calculate_line_flux(specviz_helper)
    assert_quantity_allclose(float(lineflux_result['result']) * u.Unit(lineflux_result['unit']),
                             1*u.Unit('W/m2'))


@pytest.mark.filterwarnings(r"ignore:.* contains multiple slashes")
def test_unit_gaussian_mixed_units_per_steradian(specviz_helper):
    '''
    A special unit test of Area 1 with mixed units. Should return W/m2sr
    Test provided by Patrick Ogle
    '''
    # unit-flux gaussian in wavelength space, mixed units, per steradian
    lam_a = np.arange(1, 2, 0.001)*u.Angstrom
    flx_wave = _gauss_with_unity_area(lam_a.value, mn, sig)*1E3*u.erg/u.s/u.cm**2/u.Angstrom/u.sr
    fl_wave = Spectrum1D(spectral_axis=lam_a, flux=flx_wave)

    specviz_helper.load_data(fl_wave)
    lineflux_result = _calculate_line_flux(specviz_helper)
    assert_quantity_allclose(float(lineflux_result['result']) * u.Unit(lineflux_result['unit']),
                             1*u.Unit('W/(m2sr)'))
