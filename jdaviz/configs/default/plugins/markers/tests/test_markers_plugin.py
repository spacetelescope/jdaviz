import numpy as np
from numpy.testing import assert_allclose

from jdaviz.core.marks import MarkersMark
from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_NoWCS


def _get_markers_from_viewer(viewer):
    return [m for m in viewer.figure.marks if isinstance(m, MarkersMark)][0]


def _assert_dict_allclose(dict1, dict2):
    assert dict1.keys() == dict2.keys()
    for k, v in dict1.items():
        if isinstance(v, float):
            assert_allclose(v, dict2.get(k))
        elif isinstance(v, (tuple, list)):
            assert_allclose(np.asarray(v), np.asarray(dict2.get(k)))
        else:
            assert v == dict2.get(k)


def test_markers_cubeviz(cubeviz_helper, spectrum1d_cube):
    cubeviz_helper.load_data(spectrum1d_cube, "test")
    fv = cubeviz_helper.app.get_viewer('flux-viewer')
    sv = cubeviz_helper.app.get_viewer('spectrum-viewer')

    label_mouseover = cubeviz_helper.app.session.application._tools['g-coords-info']

    mp = cubeviz_helper.plugins['Markers']
    mp.keep_active = True

    # test event in flux viewer
    label_mouseover._viewer_mouse_event(fv,
                                        {'event': 'mousemove',
                                         'domain': {'x': 0, 'y': 0}})

    assert label_mouseover.as_text() == ('Pixel x=00.0 y=00.0 Value +8.00000e+00 Jy',
                                         'World 13h39m59.9731s +27d00m00.3600s (ICRS)',
                                         '204.9998877673 27.0001000000 (deg)')

    _assert_dict_allclose(label_mouseover.as_dict(), {'axes_x': 0,
                                                      'axes_x:unit': 'pix',
                                                      'axes_y': 0,
                                                      'axes_y:unit': 'pix',
                                                      'data_label': 'test[FLUX]',
                                                      'slice': 1.0,
                                                      'spectral_axis': 4.62360027696835e-07,
                                                      'spectral_axis:unit': 'm',
                                                      'world': (204.99988776727642,
                                                                27.000099999955538),
                                                      'world:unreliable': False,
                                                      'pixel': (0, 0),
                                                      'pixel:unreliable': False,
                                                      'value': 8.0,
                                                      'value:unit': 'Jy',
                                                      'value:unreliable': False})

    mp._obj._on_viewer_key_event(fv, {'event': 'keydown',
                                      'key': 'm'})
    assert len(mp.export_table()) == 1
    assert len(_get_markers_from_viewer(fv).x) == 1

    # test event in spectrum viewer (with auto layer detection)
    # x = [4.62280007e-07, 4.62360028e-07]
    # y = [28, 92] Jy
    label_mouseover._viewer_mouse_event(sv,
                                        {'event': 'mousemove',
                                         'domain': {'x': 4.623e-7, 'y': 0}})

    assert label_mouseover.as_text() == ('Cursor 4.62300e-07, 0.00000e+00 Value +8.00000e+00 Jy',
                                         'Wave 4.62280e-07 m (0 pix)',
                                         'Flux 2.80000e+01 Jy')
    assert label_mouseover.as_dict() == {'data_label': 'test[FLUX]',
                                         'axes_x': 4.622800069238093e-07,
                                         'axes_x:unit': 'm',
                                         'slice': 0.0,
                                         'spectral_axis': 4.622800069238093e-07,
                                         'spectral_axis:unit': 'm',
                                         'axes_y': 28.0,
                                         'axes_y:unit': 'Jy',
                                         'value': 28.0,
                                         'value:unit': 'Jy'}

    mp._obj._on_viewer_key_event(sv, {'event': 'keydown',
                                      'key': 'm'})
    assert len(mp.export_table()) == 2
    assert len(_get_markers_from_viewer(fv).x) == 1
    assert len(_get_markers_from_viewer(sv).x) == 1

    # test event in spectrum viewer (with cursor only)
    label_mouseover.dataset_selected = 'none'
    label_mouseover._viewer_mouse_event(sv,
                                        {'event': 'mousemove',
                                         'domain': {'x': 4.623e-7, 'y': 0}})

    assert label_mouseover.as_text() == ('Cursor 4.62300e-07, 0.00000e+00 Value +8.00000e+00 Jy',
                                         '', '')
    assert label_mouseover.as_dict() == {'axes_x': 4.623e-07,
                                         'axes_x:unit': 'm',
                                         'axes_y': 0,
                                         'axes_y:unit': 'Jy',
                                         'data_label': '',
                                         'spectral_axis': 4.623e-07,
                                         'spectral_axis:unit': 'm',
                                         'value': 0,
                                         'value:unit': 'Jy'}

    mp._obj._on_viewer_key_event(sv, {'event': 'keydown',
                                      'key': 'm'})
    assert len(mp.export_table()) == 3
    assert len(_get_markers_from_viewer(fv).x) == 1
    assert len(_get_markers_from_viewer(sv).x) == 2

    # markers hide when plugin closed and keep_active = False
    mp.keep_active = False
    assert _get_markers_from_viewer(fv).visible is False
    assert _get_markers_from_viewer(sv).visible is False

    # markers re-appear when plugin re-opened
    mp._obj.plugin_opened = True
    assert _get_markers_from_viewer(fv).visible is True
    assert _get_markers_from_viewer(sv).visible is True
    assert len(_get_markers_from_viewer(fv).x) == 1
    assert len(_get_markers_from_viewer(sv).x) == 2

    # clearing table clears markers
    mp.clear_table()
    assert mp.export_table() is None
    assert len(_get_markers_from_viewer(fv).x) == 0
    assert len(_get_markers_from_viewer(sv).x) == 0


class TestImvizMultiLayer(BaseImviz_WCS_NoWCS):
    def test_markers_layer_cycle(self):
        label_mouseover = self.imviz.app.session.application._tools['g-coords-info']

        mp = self.imviz.plugins['Markers']
        mp.plugin_opened = True

        # cycle through dataset options (used for both coords info and markers)
        assert label_mouseover.dataset.choices == ['auto', 'none',
                                                   'has_wcs[SCI,1]',
                                                   'no_wcs[SCI,1]']
        assert label_mouseover.dataset.selected == 'auto'

        # auto (top, no WCS) layer
        label_mouseover._viewer_mouse_event(self.viewer,
                                            {'event': 'mousemove',
                                             'domain': {'x': 5, 'y': 5}})

        assert label_mouseover.as_text() == ('Pixel x=05.0 y=05.0 Value +5.50000e+01', '', '')
        assert label_mouseover.as_dict() == {'axes_x': 5,
                                             'axes_x:unit': 'pix',
                                             'axes_y': 5,
                                             'axes_y:unit': 'pix',
                                             'data_label': 'no_wcs[SCI,1]',
                                             'pixel': (5.0, 5.0),
                                             'pixel:unreliable': False,
                                             'value': 55.0,
                                             'value:unit': '',
                                             'value:unreliable': False}

        mp._obj._on_viewer_key_event(self.viewer, {'event': 'keydown',
                                                   'key': 'm'})
        assert len(_get_markers_from_viewer(self.viewer).x) == 1

        # no layer (cursor position only)
        label_mouseover.dataset.select_next()
        assert label_mouseover.dataset.selected == 'none'

        label_mouseover._viewer_mouse_event(self.viewer,
                                            {'event': 'mousemove',
                                             'domain': {'x': 5, 'y': 5}})

        assert label_mouseover.as_text() == ('Pixel x=05.0 y=05.0', '', '')
        assert label_mouseover.as_dict() == {'axes_x': 5,
                                             'axes_x:unit': 'pix',
                                             'axes_y': 5,
                                             'axes_y:unit': 'pix',
                                             'data_label': '',
                                             'pixel': (5.0, 5.0),
                                             'pixel:unreliable': False}

        mp._obj._on_viewer_key_event(self.viewer, {'event': 'keydown',
                                                   'key': 'm'})
        assert len(_get_markers_from_viewer(self.viewer).x) == 2

        # non-default layer (with WCS)
        label_mouseover.dataset.selected = 'has_wcs[SCI,1]'
        label_mouseover._viewer_mouse_event(self.viewer,
                                            {'event': 'mousemove',
                                             'domain': {'x': 5, 'y': 5}})

        assert label_mouseover.as_text() == ('Pixel x=05.0 y=05.0 Value +5.50000e+01',
                                             'World 22h30m04.5107s -20d49m54.9990s (ICRS)',
                                             '337.5187947654 -20.8319441647 (deg)')
        _assert_dict_allclose(label_mouseover.as_dict(), {'axes_x': 5,
                                                          'axes_x:unit': 'pix',
                                                          'axes_y': 5,
                                                          'axes_y:unit': 'pix',
                                                          'data_label': 'has_wcs[SCI,1]',
                                                          'world': (337.5187947653852,
                                                                    -20.831944164705973),
                                                          'world:unreliable': False,
                                                          'pixel': (5.0, 5.0),
                                                          'pixel:unreliable': False,
                                                          'value': 55.0,
                                                          'value:unit': '',
                                                          'value:unreliable': False})

        mp._obj._on_viewer_key_event(self.viewer, {'event': 'keydown',
                                                   'key': 'm'})
        assert len(_get_markers_from_viewer(self.viewer).x) == 3

    def test_markers_custom_viewer(self):
        label_mouseover = self.imviz.app.session.application._tools['g-coords-info']

        mp = self.imviz.plugins['Markers']
        mp.plugin_opened = True

        nv = self.imviz.create_image_viewer()
        self.imviz.app.add_data_to_viewer('imviz-1', 'has_wcs[SCI,1]')

        assert label_mouseover.dataset.choices == ['auto', 'none',
                                                   'has_wcs[SCI,1]',
                                                   'no_wcs[SCI,1]']
        assert label_mouseover.dataset.selected == 'auto'

        # top-layer in default viewer is no_wcs[SCI,1]
        label_mouseover._viewer_mouse_event(self.viewer,
                                            {'event': 'mousemove',
                                             'domain': {'x': 5, 'y': 5}})
        assert label_mouseover.as_dict()['data_label'] == 'no_wcs[SCI,1]'

        # top-layer in new viewer is has_wcs[SCI,1]
        label_mouseover._viewer_mouse_event(nv,
                                            {'event': 'mousemove',
                                             'domain': {'x': 5, 'y': 5}})
        assert label_mouseover.as_dict()['data_label'] == 'has_wcs[SCI,1]'

        # choosing a dataset that is in one viewer but not the other
        label_mouseover.dataset.selected = 'no_wcs[SCI,1]'
        label_mouseover._viewer_mouse_event(self.viewer,
                                            {'event': 'mousemove',
                                             'domain': {'x': 5, 'y': 5}})
        assert label_mouseover.as_dict()['data_label'] == 'no_wcs[SCI,1]'

        label_mouseover._viewer_mouse_event(nv,
                                            {'event': 'mousemove',
                                             'domain': {'x': 5, 'y': 5}})
        assert label_mouseover.as_dict()['data_label'] == ''
