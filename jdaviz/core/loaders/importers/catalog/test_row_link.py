from astropy.nddata import NDData
from astropy.table import QTable
import numpy as np


def test_row_data_association(deconfigged_helper, image_2d_wcs):
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
