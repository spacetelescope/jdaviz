import astropy.units as u
import pytest

from jdaviz import Cubeviz


cube_label = "Test Cube"

MJy_sr_test_cases = [
    # If TELESCOP and PIXAR_SR exists in main meta, Line Flux should be multiplied by this value
    # in units of steradians which should drop the steradian from the unit
    # BUT when summed over spaxels (i.e. min, max, and sum, NOT median nor mode)
    {'metadata': {'TELESCOP': 'JWST', 'PIXAR_SR': '1'},
     'expected_flux_units': {'maximum': u.Unit('W/m2'),
                             'minimum': u.Unit('W/m2'),
                             'sum': u.Unit('W/m2'),
                             'mean': u.Unit('W/(m2*sr)'),
                             'median': u.Unit('W/(m2*sr)')}
     },
    # If there is no PIXAR_SR in the meta, it the flux unit should preserve the steradian unit
    {'metadata': {'TELESCOP': 'JWST'},
     'expected_flux_units': {'maximum': u.Unit('W/(m2*sr)'),
                             'minimum': u.Unit('W/(m2*sr)'),
                             'sum': u.Unit('W/(m2*sr)'),
                             'mean': u.Unit('W/(m2*sr)'),
                             'median': u.Unit('W/(m2*sr)')}
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


def main_meta_collapse_test(data, metadata, expected_flux_units):
    '''
    Embeds metadata in the main meta, calculates line flux,
    and checks the units for each collapse function
    '''
    for function in expected_flux_units:
        cubeviz_helper = _initialize_cubeviz_with_collapse(function, data, cube_label)
        # Manually inject metadata
        for key in metadata:
            cubeviz_helper.app.data_collection[str(cube_label) + str('[FLUX]')
                                               ].meta[key] = metadata[key]

        flux_results = _calculate_line_flux(cubeviz_helper)
        assert u.Unit(flux_results['unit']) == expected_flux_units[function]


def primary_header_collapse_test(data, metadata, expected_flux_units):
    '''
    Embeds metadata in the primary header, calculates line flux,
    and checks the units for each collapse function
    '''
    for function in expected_flux_units:
        cubeviz_helper = _initialize_cubeviz_with_collapse(function, data, cube_label)
        # Manually inject metadata
        for key in metadata:
            cubeviz_helper.app.data_collection[str(cube_label) + str('[FLUX]')
                                               ].meta['_primary_header'][key] = metadata[key]

        flux_results = _calculate_line_flux(cubeviz_helper)
        assert u.Unit(flux_results['unit']) == expected_flux_units[function]


@pytest.mark.parametrize('test_case', MJy_sr_test_cases)
def test_MJy_sr_main_meta(spectrum1d_cube_MJy_sr, test_case):
    ''' Tests line flux units when Flux units are MJy/sr '''
    # Tests flux calculation units when the metadata is stored in the main meta
    main_meta_collapse_test(spectrum1d_cube_MJy_sr,
                            MJy_sr_test_cases['metadata'],
                            MJy_sr_test_cases['expected_flux_units'])
    # Tests flux calculation units when the metadata is stored in the primary header
    primary_header_collapse_test(spectrum1d_cube_MJy_sr,
                                 MJy_sr_test_cases['metadata'],
                                 MJy_sr_test_cases['expected_flux_units'])


def test_asdf_metadata(spectrum1d_cube_MJy_sr):
    '''
    Test that Line analysis can find the JWST telescope if it's given in the ASDF meta,
    ignoring the PIXAR_SR value
    '''
    asdf_test_case = {'metadata': {'telescope': 'JWST', 'PIXAR_SR': '1'},
                      'expected_flux_units': {'maximum': u.Unit('W/m2'),
                                              'minimum': u.Unit('W/m2'),
                                              'sum': u.Unit('W/m2'),
                                              'mean': u.Unit('W/(m2*sr)'),
                                              'median': u.Unit('W/(m2*sr)')}
                      }
    main_meta_collapse_test(spectrum1d_cube_MJy_sr, asdf_test_case)


def test_Jy(spectrum1d_cube):
    ''' If the Flux Unit has no steradians to begin with, Line Flux should be reported in W/m2 '''
    Jy_test_case = {'metadata': {'TELESCOP': 'JWST', 'PIXAR_SR': '1'},
                    'expected_flux_units': {'maximum': u.Unit('W/m2'),
                                            'minimum': u.Unit('W/m2'),
                                            'sum': u.Unit('W/m2'),
                                            'mean': u.Unit('W/m2'),
                                            'median': u.Unit('W/m2')}
                    }
    main_meta_collapse_test(spectrum1d_cube,
                            Jy_test_case['metadata'],
                            Jy_test_case['expected_flux_units'])
