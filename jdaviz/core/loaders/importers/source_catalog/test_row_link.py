from astropy.nddata import NDData
from astropy.table import QTable
import numpy as np


def test_row_data_association(deconfigged_helper, image_2d_wcs):
    deconfigged_helper._app.state.dev_mos_loader = True
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
    assert cat.find_component_id('Data: Image') is not None

    vc = deconfigged_helper.new_viewers['Scatter']
    vc.viewer_label = "Test Scatter"
    vc()

    assert cat.find_component_id('Data: Test Scatter') is not None

    deconfigged_helper._app.vue_destroy_viewer_item('Image')

    assert cat.find_component_id('Data: Image') is None


def test_row_data_association_disabled_without_dev_flag(deconfigged_helper, image_2d_wcs,
                                                        sky_coord_only_source_catalog):
    app = deconfigged_helper._app
    assert app.state.dev_mos_loader is False

    deconfigged_helper.load(NDData(np.ones((32, 32)), wcs=image_2d_wcs), data_label='image')
    loader = deconfigged_helper.loaders['object']
    loader.object = sky_coord_only_source_catalog
    loader.format = 'Source Catalog'
    loader.importer.viewer.create_new = 'Source Catalog Table'
    loader.load()

    catalog = next(data for data in app.data_collection
                   if data.meta.get('_importer') == 'SourceCatalogImporter')
    table_viewer = deconfigged_helper.viewers['Source Catalog Table']._obj.glue_viewer

    assert not catalog.meta.get('_viewer_data_columns')
    assert all(not str(component).startswith('Data: ')
               for component in catalog.components)
    assert all(not header['value'].startswith('Data: ')
               for header in table_viewer.widget_table._get_headers())
    assert not any(item['value'].startswith('Data: ')
                   for item in table_viewer.toolbar.tools['jdaviz:table_columns_visible']
                   ._build_custom_widgets()[0]['items'])
    table_viewer.toolbar._update_tool_visibilities()
    assert not table_viewer.toolbar.tools_data['jdaviz:table_row_select']['visible']
