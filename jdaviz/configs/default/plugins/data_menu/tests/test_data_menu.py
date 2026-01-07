import numpy as np
from astropy.nddata import NDData
from regions import CirclePixelRegion, PixCoord


def test_load_nddata(imviz_helper):
    data_a = NDData(np.random.rand(16, 16))
    data_a1 = NDData(np.random.rand(16, 16))
    data_b = NDData(np.random.rand(16, 16))
    data_b1 = NDData(np.random.rand(16, 16))
    data_b2 = NDData(np.random.rand(16, 16))
    data_c = NDData(np.random.rand(16, 16))

    imviz_helper.load(data_a, data_label='data_a')
    imviz_helper.load(data_a1, data_label='data_a1', parent='data_a[DATA]')
    imviz_helper.load(data_b, data_label='data_b')
    imviz_helper.load(data_b1, data_label='data_b1', parent='data_b[DATA]')
    imviz_helper.load(data_b2, data_label='data_b2', parent='data_b[DATA]')
    imviz_helper.load(data_c, data_label='data_c')

    dm = imviz_helper.viewers['imviz-0'].data_menu._obj
    gv = imviz_helper.viewers['imviz-0']._obj.glue_viewer

    assert ([x['zorder'] for x in dm.layer_items
             if x['label'] == 'data_c[DATA]'][0] == 6)

    # Go from 6 to 4, should redirect zorder to be 3
    # AKA below the block of data_b + children
    gv.state.layers[5].zorder = 4
    dm.layer._update_items()

    assert ([x['zorder'] for x in dm.layer_items
             if x['label'] == 'data_c[DATA]'][0] == 3)

    # Set layer with 'data_c[DATA]' to be invisible
    imviz_helper.viewers['imviz-0'].data_menu.set_layer_visibility(
        'data_c[DATA]', False)

    assert ([x['zorder'] for x in dm.layer_items
             if x['label'] == 'data_c[DATA]'][0] == 3)

    gv.state.layers[5].zorder = 1
    dm.layer._update_items()

    assert ([x['zorder'] for x in dm.layer_items
             if x['label'] == 'data_c[DATA]'][0] == 1)


def test_rename_data_and_subsets(deconfigged_helper, image_hdu_wcs):
    """
    Test renaming both data and subsets via dm.rename.
    """
    # Load data
    deconfigged_helper.load(image_hdu_wcs, format='Image', data_label='original_data')

    # Create a subset
    subset_plugin = deconfigged_helper.plugins['Subset Tools']
    reg = CirclePixelRegion(center=PixCoord(x=8, y=8), radius=3)
    subset_plugin.import_region(reg)

    # Get the data menu
    dm = deconfigged_helper.viewers['Image'].data_menu._obj

    # Test renaming data
    dm.rename('original_data', 'renamed_data')
    assert 'renamed_data' in [x['label'] for x in dm.layer_items]
    assert 'original_data[DATA]' not in [x['label'] for x in dm.layer_items]

    # Test renaming subset
    dm.rename('Subset 1', 'my subset')
    assert 'my subset' in [x['label'] for x in dm.layer_items]
    assert 'Subset 1' not in [x['label'] for x in dm.layer_items]
