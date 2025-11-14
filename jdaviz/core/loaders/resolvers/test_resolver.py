from jdaviz.app import Application
from jdaviz.core.loaders.resolvers.resolver import BaseResolver, find_closest_polygon_mark

import numpy as np
from astropy.nddata import NDData
from astropy.table import Table
from astropy.wcs import WCS


# Create a minimal test class that mimics the resolver behavior
# without this we get an error when attempting to use BaseResolver directly
class TestBaseResolver(BaseResolver):
    template = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


def test_server_is_remote_callback():
    # Create app instance
    app = Application()

    # Test the sync
    test_obj = TestBaseResolver(app=app)
    settings = app.state.settings

    # Check default
    assert settings.get('server_is_remote') is False
    assert settings.get('server_is_remote') == test_obj.server_is_remote

    settings['server_is_remote'] = True
    assert settings.get('server_is_remote') == test_obj.server_is_remote

    # Ensure setting test_obj.server_is_remote does not backpropagate
    # (this behavior could change)
    test_obj.server_is_remote = False
    assert settings.get('server_is_remote') != test_obj.server_is_remote


def test_footprint_workflow(imviz_helper):

    wcs = WCS({
        'CTYPE1': 'RA---TAN', 'CUNIT1': 'deg', 'CDELT1': -0.0002777777778,
        'CRPIX1': 1, 'CRVAL1': 337.5202808,
        'CTYPE2': 'DEC--TAN', 'CUNIT2': 'deg', 'CDELT2': 0.0002777777778,
        'CRPIX2': 1, 'CRVAL2': -20.83333306,
    })
    arr = np.ones((200, 200))
    ndd = NDData(arr, wcs=wcs)
    imviz_helper.load_data(ndd, data_label='test_image')

    table = Table()
    table['Dataset'] = ['obs1', 'obs2', 'obs3']
    table['s_region'] = [
        'POLYGON 337.51 -20.84 337.52 -20.84 337.52 -20.83 337.51 -20.83',
        'POLYGON 337.52 -20.84 337.53 -20.84 337.53 -20.83 337.52 -20.83',
        'POLYGON 337.53 -20.84 337.54 -20.84 337.54 -20.83 337.53 -20.83',
    ]

    ldr = imviz_helper.loaders['object']
    ldr.object = table
    resolver = ldr._obj

    resolver.treat_table_as_query = True

    assert resolver.parsed_input_is_query is True
    assert resolver.observation_table_populated is True
    assert 's_region' in resolver.observation_table.headers_avail

    resolver.vue_link_by_wcs()
    assert resolver.is_wcs_linked is True

    resolver.toggle_custom_toolbar()
    assert resolver.custom_toolbar_enabled is True
    assert len(resolver._footprint_marks) == 3
    assert len(resolver._footprint_groups) == 3
    assert all(idx in resolver._footprint_groups for idx in range(3))

    mark = resolver._footprint_marks[1]
    px, py = np.mean(mark.x), np.mean(mark.y)
    idx = find_closest_polygon_mark(px, py, resolver._footprint_marks)
    assert idx is not None
    assert 0 <= idx < 3

    resolver.toggle_custom_toolbar()
    assert resolver.custom_toolbar_enabled is False
    assert resolver._footprint_marks == []
    assert resolver._footprint_groups == {}
