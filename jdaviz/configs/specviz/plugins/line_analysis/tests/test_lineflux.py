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


def _calculate_line_flux(viz_helper):
    '''
    Returns the line flux calculation by opening the Line Analysis Plugin
    Assumes the plugin hasn't been opened yet
    '''
    # Open the plugin and force the calculation
    viz_helper.app.state.drawer = True
    line_analysis_plugin = viz_helper.app.get_tray_item_from_name('specviz-line-analysis')
    line_analysis_plugin.open_in_tray()
    # Retrieve Results
    for result in line_analysis_plugin.results:
        if result['function'] == 'Line Flux':
            return result


@pytest.mark.filterwarnings('ignore')
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

        autocollapsed_spectrum_unit = cubeviz_helper.specviz.get_spectra()[data_label + "[FLUX]"
                                                                           ].flux.unit
        # Futureproofing: Eventually Cubeviz autocollapse will change the flux units of the
        # spectra depending on whether the spectrum was collapsed OVER SPAXELS or not. Only
        # do the assertion check if we KNOW what the expected lineflux results should be
        if autocollapsed_spectrum_unit in expected_lineflux_results.keys():
            assert u.Unit(lineflux_result['unit']) == expected_lineflux_results[spectra_fluxunit]


def test_unit_gaussian_lineflux(specviz_helper):
    '''
    Test an Area 1 Gaussian and ensure the result returns in W/m2
    Test provided by Patrick Ogle
    '''
    # Gaussian function with area = 1 Jy*Hz
    def gauss_with_unity_area(x, mean, sigma):
        dx = x - mean
        n = 1/(sigma*np.sqrt(2*np.pi))
        g = n * np.exp(-dx**2/(2*sigma**2))
        return g
    # unit-flux gaussian in frequency space
    freq = np.arange(1, 2, 0.001)*u.Hz
    mn = 1.5
    sig = 0.01
    flux = gauss_with_unity_area(freq.value, mn, sig)*u.Jy
    specviz_helper.load_data(Spectrum1D(spectral_axis=freq, flux=flux))

    lineflux_result = _calculate_line_flux(specviz_helper)
    assert_quantity_allclose(float(lineflux_result['result']) * u.Unit(lineflux_result['unit']),
                             1e-26*u.Unit('W/m2'))
