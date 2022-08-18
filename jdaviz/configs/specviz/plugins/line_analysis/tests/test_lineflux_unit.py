import astropy.units as u
from glue.viewers.profile.state import FUNCTIONS as COLLAPSE_FUNCTIONS
import pytest

from jdaviz import Cubeviz


test_cases = [
    {'data_fixture': 'spectrum1d_cube_MJy_sr',
     'expected_lineflux_unit': u.Unit('W/(m2*sr)')
     },
    {'data_fixture': 'spectrum1d_cube',
     'expected_lineflux_unit': u.Unit('W/m2')
     }
]

def _calculate_line_flux(function, dataset):
    '''
    Returns the line flux calculation for a particular collapse function
    by opening the Line Analysis Plugin
    '''

    # Initialize Cubeviz with specific data and collapse function
    cubeviz_helper = Cubeviz()
    cubeviz_helper.load_data(dataset)
    cubeviz_helper.app.get_viewer('spectrum-viewer').state.function = function

    # Open the plugin and force the calculation
    cubeviz_helper.app.state.drawer = True
    plugin_index = [ti['name'] for ti in cubeviz_helper.app.state.tray_items
                    ].index('specviz-line-analysis')
    cubeviz_helper.app.state.tray_items_open = [plugin_index]

    # Retrieve Results
    plugin = cubeviz_helper.app.get_tray_item_from_name('specviz-line-analysis')
    for result in plugin.results:
        if result['function'] == 'Line Flux':
            return result


@pytest.mark.parametrize('test_case', test_cases)
def test_flux_collapse_units(test_case, request):
    ''' Calculates line flux and checks the units for each collapse function '''
    data = request.getfixturevalue(test_case['data_fixture'])
    expected_lineflux_unit = test_case['expected_lineflux_unit']
    for function in COLLAPSE_FUNCTIONS:
        flux_results = _calculate_line_flux(function, data)
        assert u.Unit(flux_results['unit']) == expected_lineflux_unit
