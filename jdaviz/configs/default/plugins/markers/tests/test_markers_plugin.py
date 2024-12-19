import os

import astropy.units as u
import numpy as np
from numpy.testing import assert_allclose
import pytest
from specutils import Spectrum1D

from jdaviz.core.custom_units_and_equivs import PIX2, SPEC_PHOTON_FLUX_DENSITY_UNITS
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


def test_markers_cubeviz(tmp_path, cubeviz_helper, spectrum1d_cube):
    cubeviz_helper.load_data(spectrum1d_cube, "test")
    fv = cubeviz_helper.app.get_viewer('flux-viewer')
    sv = cubeviz_helper.app.get_viewer('spectrum-viewer')
    sb_unit = 'Jy / pix2'  # cubes loaded in Jy have sb unit of Jy / pix2
    flux_unit = 'Jy'

    label_mouseover = cubeviz_helper.app.session.application._tools['g-coords-info']

    mp = cubeviz_helper.plugins['Markers']
    mp.keep_active = True
    exp = cubeviz_helper.plugins['Export']

    # no marks yet, so table does not yet appear in export plugin
    assert "Markers: table" not in exp.plugin_table.choices

    # test event in flux viewer
    label_mouseover._viewer_mouse_event(fv,
                                        {'event': 'mousemove',
                                         'domain': {'x': 0, 'y': 0}})

    assert label_mouseover.as_text() == (f'Pixel x=00.0 y=00.0 Value +8.00000e+00 {sb_unit}',
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
                                                      'world_ra': 204.99988776727642,
                                                      'world_dec': 27.000099999955538,
                                                      'world:unreliable': False,
                                                      'pixel_x': 0,
                                                      'pixel_y': 0,
                                                      'pixel:unreliable': False,
                                                      'value': 8.0,
                                                      'value:unit': sb_unit,
                                                      'value:unreliable': False})

    mp._obj._on_viewer_key_event(fv, {'event': 'keydown',
                                      'key': 'm'})
    assert len(mp.export_table()) == 1
    assert len(_get_markers_from_viewer(fv).x) == 1

    # test event in spectrum viewer (with auto layer detection)
    # x = [4.62280007e-07, 4.62360028e-07]
    # y = [28, 92] Jy / pix2
    label_mouseover._viewer_mouse_event(sv,
                                        {'event': 'mousemove',
                                         'domain': {'x': 4.623e-7, 'y': 0}})

    assert label_mouseover.as_text() == (f'Cursor 4.62300e-07, 0.00000e+00 Value +8.00000e+00 {sb_unit}',  # noqa
                                         'Wave 4.62280e-07 m (0 pix)',
                                         f'Flux 2.80000e+01 {flux_unit}')
    assert label_mouseover.as_dict() == {'data_label': 'Spectrum (sum)',
                                         'axes_x': 4.622800069238093e-07,
                                         'axes_x:unit': 'm',
                                         'slice': 0.0,
                                         'spectral_axis': 4.622800069238093e-07,
                                         'spectral_axis:unit': 'm',
                                         'axes_y': 28.0,
                                         'axes_y:unit': flux_unit,
                                         'value': 28.0,
                                         'value:unit': flux_unit}

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

    assert label_mouseover.as_text() == (f'Cursor 4.62300e-07, 0.00000e+00 Value +8.00000e+00 {sb_unit}',  # noqa
                                         '', '')
    assert label_mouseover.as_dict() == {'axes_x': 4.623e-07,
                                         'axes_x:unit': 'm',
                                         'axes_y': 0,
                                         'axes_y:unit': flux_unit,
                                         'data_label': '',
                                         'spectral_axis': 4.623e-07,
                                         'spectral_axis:unit': 'm',
                                         'value': 0,
                                         'value:unit': flux_unit}

    mp._obj._on_viewer_key_event(sv, {'event': 'keydown',
                                      'key': 'm'})

    # test that markers update on unit conversion
    uc = cubeviz_helper.plugins['Unit Conversion']
    uc.flux_unit.selected = 'MJy'

    # find the index of the marker's x-coordinate in the spectral axis of the original input data
    spec = cubeviz_helper.get_data('Spectrum (sum)', use_display_units=True)
    marker_index = np.where(spec.spectral_axis.value == mp._obj.marks['cubeviz-2'].x)
    # use the index to find the associated flux value of the original input
    flux_value = spec.flux[marker_index].value

    # compare the marker's (y) flux value with the flux value of the original input data
    assert_allclose(mp._obj.marks['cubeviz-2'].y[0], flux_value)

    # now check if marks update with a unit that requires spectral density equivalency
    uc.flux_unit.selected = 'erg / (Angstrom s cm2)'

    spec = cubeviz_helper.get_data('Spectrum (sum)', use_display_units=True)
    flux_value = spec.flux[marker_index].value

    assert_allclose(mp._obj.marks['cubeviz-2'].y[0], flux_value)

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

    # appears as option in export plugin and exports successfully
    assert "Markers: table" in exp.plugin_table.choices
    filename = str(tmp_path / "cubeviz_export.ecsv")
    exp.filename.auto = False
    exp.filename.value = filename
    exp.plugin_table = "Markers: table"
    exp.export()
    assert os.path.isfile(filename)

    # Also exports to CSV
    filename_2 = str(tmp_path / "cubeviz_export.csv")
    exp.plugin_table_format.selected = 'csv'
    exp.filename.value = filename_2
    exp.export()
    assert os.path.isfile(filename_2)

    # clearing table clears markers
    mp.clear_table()
    assert mp.export_table() is None
    assert len(_get_markers_from_viewer(fv).x) == 0
    assert len(_get_markers_from_viewer(sv).x) == 0


@pytest.mark.parametrize("flux_unit", [u.Unit(x) for x in SPEC_PHOTON_FLUX_DENSITY_UNITS])
@pytest.mark.parametrize("angle_unit", [u.sr, PIX2])
@pytest.mark.parametrize("new_flux_unit", [u.Unit(x) for x in SPEC_PHOTON_FLUX_DENSITY_UNITS])
def test_markers_cubeviz_flux_unit_conversion(cubeviz_helper,
                                              spectrum1d_cube_custom_fluxunit,
                                              flux_unit, angle_unit, new_flux_unit):
    """
    Test the markers plugin with all possible unit conversions for
    cubes in spectral/photon surface brightness units (e.g. Jy/sr, Jy/pix2).

    The markers plugin should respect the choice of flux and angle
    unit selected in the Unit Conversion plugin, and inputs and results should
    be converted based on selection. All conversions between units in the
    flux dropdown menu in the unit conversion plugin should be supported.
    """

    if new_flux_unit == flux_unit:  # skip 'converting' to same unit
        return

    new_flux_unit_str = new_flux_unit.to_string()

    # load cube with specified unit
    cube = spectrum1d_cube_custom_fluxunit(fluxunit=flux_unit / angle_unit,
                                           shape=(5, 5, 4),
                                           with_uncerts=True)
    cubeviz_helper.load_data(cube, data_label="test")

    # get plugins
    mp = cubeviz_helper.plugins['Markers']
    uc = cubeviz_helper.plugins['Unit Conversion']._obj

    mp.keep_active = True

    fv = cubeviz_helper.app.get_viewer('flux-viewer')
    label_mouseover = cubeviz_helper.app.session.application._tools['g-coords-info']
    label_mouseover._viewer_mouse_event(fv,
                                        {'event': 'mousemove',
                                         'domain': {'x': 0, 'y': 0}})
    mp._obj._on_viewer_key_event(fv, {'event': 'keydown',
                                      'key': 'm'})

    # set to new unit
    uc.flux_unit.selected = new_flux_unit_str
    new_cube_unit_str = (new_flux_unit / angle_unit).to_string()

    # add a new marker at the same location
    label_mouseover._viewer_mouse_event(fv,
                                        {'event': 'mousemove',
                                         'domain': {'x': 0,
                                                    'y': 0}})
    # mouseover should have changed to new unit
    assert label_mouseover.as_dict()['value:unit'] == new_cube_unit_str

    mp._obj._on_viewer_key_event(fv, {'event': 'keydown',
                                      'key': 'm'})

    # make sure last marker added to table reflects new unit selection
    last_row = mp.export_table()[-1]
    assert last_row['value:unit'] == new_cube_unit_str


def test_markers_specviz2d_unit_conversion(specviz2d_helper, spectrum2d):
    data = np.zeros((5, 10))
    data[3] = np.arange(10)
    spectrum2d = Spectrum1D(flux=data*u.MJy, spectral_axis=data[3]*u.AA)
    specviz2d_helper.load_data(spectrum2d)

    uc = specviz2d_helper.plugins['Unit Conversion']
    uc.open_in_tray()
    mp = specviz2d_helper.plugins['Markers']
    mp.keep_active = True

    label_mouseover = specviz2d_helper.app.session.application._tools["g-coords-info"]
    viewer2d = specviz2d_helper.app.get_viewer("spectrum-2d-viewer")
    label_mouseover._viewer_mouse_event(viewer2d, {"event": "mousemove",
                                                   "domain": {"x": 6, "y": 3}})
    assert label_mouseover.as_text() == ('Pixel x=06.0 y=03.0 Value +6.00000e+00 MJy',
                                         'Wave 6.00000e+00 Angstrom',
                                         '')
    mp._obj._on_viewer_key_event(viewer2d, {'event': 'keydown',
                                            'key': 'm'})

    # make sure last marker added to table reflects new unit selection
    last_row = mp.export_table()[-1]
    assert last_row['value:unit'] == uc.flux_unit
    assert last_row['spectral_axis:unit'] == uc.spectral_unit

    # ensure marks work with flux conversion where spectral axis is required and
    # spectral axis conversion
    uc.flux_unit = 'erg / (Angstrom s cm2)'
    uc.spectral_unit = 'Ry'
    label_mouseover._viewer_mouse_event(viewer2d, {"event": "mousemove",
                                                   "domain": {"x": 4, "y": 3}})
    assert label_mouseover.as_text() == ('Pixel x=04.0 y=03.0 Value +7.49481e+00 erg / (Angstrom s cm2)',  # noqa
                                         'Wave 2.27817e+02 Ry',
                                         '')
    mp._obj._on_viewer_key_event(viewer2d, {'event': 'keydown',
                                            'key': 'm'})

    # make sure last marker added to table reflects new unit selection
    last_row = mp.export_table()[-1]
    assert last_row['value:unit'] == uc.flux_unit
    assert last_row['spectral_axis:unit'] == uc.spectral_unit

    second_marker_flux_unit = uc.flux_unit.selected
    second_marker_spectral_unit = uc.spectral_unit.selected

    # test edge case two non-native spectral axis required conversions
    uc.flux_unit = 'ph / (Angstrom s cm2)'
    uc.spectral_unit = 'eV'

    # make sure table flux and spectral unit doesn't update
    assert last_row['value:unit'] == second_marker_flux_unit
    assert last_row['spectral_axis:unit'] == second_marker_spectral_unit


class TestImvizMultiLayer(BaseImviz_WCS_NoWCS):
    def test_markers_layer_cycle(self):
        label_mouseover = self.imviz.app.session.application._tools['g-coords-info']

        mp = self.imviz.plugins['Markers']
        mp._obj.plugin_opened = True

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
                                             'pixel_x': 5.0,
                                             'pixel_y': 5.0,
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
                                             'pixel_x': 5.0,
                                             'pixel_y': 5.0,
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
                                                          'world_ra': 337.5187947653852,
                                                          'world_dec': -20.831944164705973,
                                                          'world:unreliable': False,
                                                          'pixel_x': 5.0,
                                                          'pixel_y': 5.0,
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
        mp._obj.plugin_opened = True

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
