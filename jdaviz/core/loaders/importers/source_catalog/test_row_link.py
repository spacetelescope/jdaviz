from astropy.nddata import NDData
from astropy.table import QTable
import numpy as np
import pytest


@pytest.mark.parametrize('dev_mos_loader', [True, False])
def test_row_data_association(deconfigged_helper, image_2d_wcs, dev_mos_loader):
    app = deconfigged_helper._app
    assert app.state.dev_mos_loader is False
    app.state.dev_mos_loader = dev_mos_loader
    # Create a table to load
    ra = "ra"
    dec = "dec"
    tab = QTable({ra: [10.0], dec: [-5.0]})

    # Load the table as a catalog but don't add it to a table viewer yet
    ldr = deconfigged_helper.loaders['object']
    ldr.object = tab
    ldr.format = 'Source Catalog'
    ldr.importer.viewer = []
    ldr.load()

    # Load two images into an image viewer
    data = NDData(np.ones((128, 128)), wcs=image_2d_wcs)
    deconfigged_helper.load(data, data_label="ImData1")
    deconfigged_helper.load(data, data_label="ImData2")
    deconfigged_helper.plugins['Orientation'].align_by = 'WCS'

    cat = deconfigged_helper._app.data_collection[0]

    # Make sure the columns are responsive to viewer changes even though
    # the catalog isn't loaded in a table viewer
    if dev_mos_loader:
        assert cat.find_component_id('Data: Image') is not None
    else:
        assert cat.find_component_id('Data: Image') is None

    vc = deconfigged_helper.new_viewers['Scatter']
    vc.viewer_label = "Test Scatter"
    vc()

    if dev_mos_loader:
        assert cat.find_component_id('Data: Test Scatter') is not None
    else:
        assert cat.find_component_id('Data: Test Scatter') is None

    # Add the catalog to a table viewer and check the row-link UI in both modes.
    vc = deconfigged_helper.new_viewers['Source Catalog Table']
    vc.dataset.select_all()
    table_viewer = vc()._obj.glue_viewer

    assert bool(cat.meta.get('_viewer_data_columns')) is dev_mos_loader
    assert any(str(component).startswith('Data: ')
               for component in cat.components) is dev_mos_loader
    assert any(header['value'].startswith('Data: ')
               for header in table_viewer.widget_table._get_headers()) is dev_mos_loader
    assert any(item['value'].startswith('Data: ')
               for item in table_viewer.toolbar.tools['jdaviz:table_columns_visible']
               ._build_custom_widgets()[0]['items']) is dev_mos_loader
    table_viewer.toolbar._update_tool_visibilities()
    assert (table_viewer.toolbar.tools_data['jdaviz:table_row_select']['visible']
            is dev_mos_loader)

    app.vue_destroy_viewer_item('Image')

    assert cat.find_component_id('Data: Image') is None
