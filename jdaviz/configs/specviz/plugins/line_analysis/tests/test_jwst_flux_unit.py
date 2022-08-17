import astropy.units as u
from glue.viewers.profile.state import FUNCTIONS as COLLAPSE_FUNCTIONS
import pytest

from jdaviz import Cubeviz


cube_label = "Test Cube"

test_cases = [
    {'data_fixture': 'spectrum1d_cube_MJy_sr',
     'expected_lineflux_unit': u.Unit('W/(m2*sr)')
     },
    {'data_fixture': 'spectrum1d_cube',
     'expected_lineflux_unit': u.Unit('W/m2')
     }
]


def _initialize_cubeviz_with_collapse(function, dataset, label):
    ''' Initializes Cubeviz with specific data and collapse function '''
    cubeviz_helper = Cubeviz()
    cubeviz_helper.load_data(dataset, data_label=label)
    cubeviz_helper.app.get_viewer('spectrum-viewer').state.function = function
    return cubeviz_helper


def _calculate_line_flux(cubeviz_helper):
    '''
    Returns the line flux calcualtion by opening the Line Analysis Plugin
    Assumes the plugin hasn't been opened yet
    '''
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


def main_meta_collapse_test(data, metadata, expected_lineflux_unit):
    '''
    Embeds metadata in the main meta, calculates line flux,
    and checks the units for each collapse function
    '''
    for function in COLLAPSE_FUNCTIONS:
        cubeviz_helper = _initialize_cubeviz_with_collapse(function, data, cube_label)
        # Manually inject metadata
        for key in metadata:
            cubeviz_helper.app.data_collection[str(cube_label) + str('[FLUX]')
                                               ].meta[key] = metadata[key]

        flux_results = _calculate_line_flux(cubeviz_helper)
        assert u.Unit(flux_results['unit']) == expected_lineflux_unit


def primary_header_collapse_test(data, metadata, expected_lineflux_unit):
    '''
    Embeds metadata in the primary header, calculates line flux,
    and checks the units for each collapse function
    '''
    for function in COLLAPSE_FUNCTIONS:
        cubeviz_helper = _initialize_cubeviz_with_collapse(function, data, cube_label)
        # Force primary_header to exist if it doesn't already
        if '_primary_header' not in cubeviz_helper.app.data_collection[(str(cube_label) +
                                                                        str('[FLUX]'))].meta:
            cubeviz_helper.app.data_collection[(str(cube_label) +
                                                str('[FLUX]'))].meta['_primary_header'] = dict()
        # Manually inject metadata
        for key in metadata:
            cubeviz_helper.app.data_collection[str(cube_label) + str('[FLUX]')
                                               ].meta['_primary_header'][key] = metadata[key]

        flux_results = _calculate_line_flux(cubeviz_helper)
        assert u.Unit(flux_results['unit']) == expected_lineflux_unit


@pytest.mark.parametrize('test_case', test_cases)
def test_MJy_sr_main_meta(test_case, request):
    ''' Tests line flux units when Flux units are MJy/sr '''
    # Tests flux calculation units when the telescope is stored in the main meta
    main_meta_collapse_test(request.getfixturevalue(test_case['data_fixture']),
                            {'TELESCOP': 'JWST'},
                            test_case['expected_lineflux_unit'])
    # Also make sure Line Analysis can find the telescope if it's stored as an ASDF keyword
    main_meta_collapse_test(request.getfixturevalue(test_case['data_fixture']),
                            {'telescope': 'JWST'},
                            test_case['expected_lineflux_unit'])
    # Lastly, test flux calculation units when the telescope is stored in the primary header
    primary_header_collapse_test(request.getfixturevalue(test_case['data_fixture']),
                                 {'TELESCOP': 'JWST'},
                                 test_case['expected_lineflux_unit'])
