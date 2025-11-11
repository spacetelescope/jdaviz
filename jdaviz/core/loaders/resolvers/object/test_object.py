import numpy as np
from astropy.nddata import NDData
from astropy.table import Table
from astropy.wcs import WCS

from jdaviz.core.loaders.resolvers.object.object import find_closest_polygon_mark


def test_footprint_workflow(imviz_helper):
    wcs = WCS({'CTYPE1': 'RA---TAN', 'CUNIT1': 'deg', 'CDELT1': -0.0002777777778,
               'CRPIX1': 1, 'CRVAL1': 337.5202808,
               'CTYPE2': 'DEC--TAN', 'CUNIT2': 'deg', 'CDELT2': 0.0002777777778,
               'CRPIX2': 1, 'CRVAL2': -20.833333059999998})

    arr = np.ones((200, 200))
    ndd = NDData(arr, wcs=wcs)
    imviz_helper.load_data(ndd, data_label='test_image')

    # Create a table with s_region column
    table = Table()
    table['obs_id'] = ['obs1', 'obs2', 'obs3']
    table['s_region'] = [
        'POLYGON 337.51 -20.84 337.52 -20.84 337.52 -20.83 337.51 -20.83',
        'POLYGON 337.52 -20.84 337.53 -20.84 337.53 -20.83 337.52 -20.83',
        'POLYGON 337.53 -20.84 337.54 -20.84 337.54 -20.83 337.53 -20.83'
    ]

    ldr = imviz_helper.loaders['object']
    ldr._obj.observation_table._clear_table()
    for row in table:
        ldr._obj.observation_table.add_item(row)
    ldr._obj.observation_table_populated = True

    ldr._obj.vue_link_by_wcs()

    # Display footprints
    ldr._obj.toggle_custom_toolbar()

    # Check if footprints were displayed
    assert len(ldr._obj._footprint_marks) == 3

    # Check if marks are in _footprint_groups
    assert len(ldr._obj._footprint_groups) == 3
    assert all(idx in ldr._obj._footprint_groups for idx in range(3))

    # identify a footprint
    mark = ldr._obj._footprint_marks[1]
    px, py = np.mean(mark.x), np.mean(mark.y)
    idx = find_closest_polygon_mark(px, py, ldr._obj._footprint_marks)
    assert idx is not None
    assert 0 <= idx < 3
