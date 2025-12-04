from jdaviz import Imviz
import numpy as np
from astropy.nddata import NDData

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

    print('Initial zorders in layer items:',
          [(x['label'], x['zorder']) for x in imviz_helper.viewers['imviz-0'].data_menu._obj.layer_items])
    print('\n\nInitial zorders in glue layers:',
          [(layer.layer.label, layer.zorder) for layer in imviz_helper.viewers['imviz-0']._obj.glue_viewer.state.layers])
    print('\n\n layer at 5', imviz_helper.viewers['imviz-0']._obj.glue_viewer.state.layers[5].layer.label)

    assert ([x['zorder'] for x in imviz_helper.viewers['imviz-0'].data_menu._obj.layer_items
            if x['label'] == 'data_c[DATA]'][0] == 6)

    # Go from 6 to 4, should redirect zorder to be 2 AKA below the block of data_b + children
    imviz_helper.viewers['imviz-0']._obj.glue_viewer.state.layers[5].zorder = 4
    imviz_helper.viewers['imviz-0'].data_menu._obj.layer._update_items()
    
    print('New zorders in layer items:',
        [(x['label'], x['zorder']) for x in imviz_helper.viewers['imviz-0'].data_menu._obj.layer_items])
    print('\n\nNew zorders in glue layers:',
        [(layer.layer.label, layer.zorder) for layer in imviz_helper.viewers['imviz-0']._obj.glue_viewer.state.layers])
    print('\n\n layer at 5', imviz_helper.viewers['imviz-0']._obj.glue_viewer.state.layers[5].layer.label)

    assert ([x['zorder'] for x in imviz_helper.viewers['imviz-0'].data_menu._obj.layer_items
        if x['label'] == 'data_c[DATA]'][0] == 2.5)

    imviz_helper.viewers['imviz-0']._obj.glue_viewer.state.layers[5].zorder = 1
    imviz_helper.viewers['imviz-0'].data_menu._obj.layer._update_items()

    assert ([x['zorder'] for x in imviz_helper.viewers['imviz-0'].data_menu._obj.layer_items
        if x['label'] == 'data_c[DATA]'][0] == 0.5)