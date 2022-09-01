import astropy.units as u
from glue.viewers.profile.state import FUNCTIONS as COLLAPSE_FUNCTIONS
import pytest

from jdaviz import Cubeviz

# Maps input spectrum flux unit to expected line analysis flux unit
expected_lineflux_results = {
    u.Jy/u.sr: u.Unit('W/(m2*sr)'),
    u.Jy: u.Unit('W/m2'),
    u.Unit('W/m2/m')/u.sr: u.Unit('W/(m2*sr)'),
    u.Unit('W/m2/m'): u.Unit('W/m2')
}

test_cases = list(expected_lineflux_results.keys())


@pytest.mark.filterwarnings()
@pytest.mark.parametrize('spectra_fluxunit', test_cases)
def test_flux_collapse_units(spectrum1d_cube_custom_fluxunit, spectra_fluxunit):
    ''' Calculates line flux and checks the units for each collapse function '''
    data = spectrum1d_cube_custom_fluxunit(spectra_fluxunit)
    for function in COLLAPSE_FUNCTIONS:
        # Initialize Cubeviz with specific data and collapse function
        cubeviz_helper = Cubeviz()
        data_label = "Test Cube"
        cubeviz_helper.load_data(data)
        cubeviz_helper.app.get_viewer('spectrum-viewer').state.function = function

        # Open the plugin and force the calculation
        cubeviz_helper.app.state.drawer = True
        line_analysis_plugin = cubeviz_helper.app.get_tray_item_from_name('specviz-line-analysis')
        line_analysis_plugin.open_in_tray()

        # Retrieve Results
        for result in line_analysis_plugin.results:
            if result['function'] == 'Line Flux':
                autocollapsed_spectrum_unit = cubeviz_helper.specviz.get_spectra()[(data_label +
                                                                                    " [FLUX]")
                                                                                   ].flux.unit
                # Futureproofing: Eventually Cubeviz autocollapse will change the flux units of the
                # spectra depending on whether the spectrum was collapsed OVER SPAXELS or not. Only
                # do the assertion check if we KNOW what the expected lineflux results should be
                if autocollapsed_spectrum_unit in expected_lineflux_results.keys():
                    assert u.Unit(result['unit']) == expected_lineflux_results[spectra_fluxunit]
