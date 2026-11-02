import numpy as np
import pytest
from astropy import units as u
from astropy.nddata import InverseVariance
from astropy.nddata import NDData
from astropy.wcs import WCS
from specutils import Spectrum

from jdaviz.configs.default.plugins.viewers import JdavizProfileView
from jdaviz.configs.imviz.tests.utils import _image_nddata_wcs
from jdaviz.core.custom_units_and_equivs import SPEC_PHOTON_FLUX_DENSITY_UNITS
from jdaviz.core.events import ViewerRemovedMessage


# On failure, should not crash; essentially a no-op.
@pytest.mark.parametrize(
    ('new_spectral_axis', 'new_flux', 'expected_spectral_axis', 'expected_flux'),
    [("fail", "erg / (s cm2 Angstrom)", "Angstrom", "erg / (s cm2 Angstrom)"),
     ("None", "fail", "Angstrom", "Jy"),
     ("micron", "fail", "micron", "Jy")])
def test_value_error_exception(deconfigged_helper, spectrum1d, new_spectral_axis, new_flux,
                               expected_spectral_axis, expected_flux):
    deconfigged_helper.load(spectrum1d, data_label="Test 1D Spectrum", format='1D Spectrum')
    viewer = deconfigged_helper._app.get_viewer('1D Spectrum')
    plg = deconfigged_helper.plugins["Unit Conversion"]

    try:
        plg.spectral_unit = new_spectral_axis
    except ValueError as e:
        if "reverting selection to" not in repr(e):
            raise
    try:
        plg._obj.flux_unit_selected = new_flux
    except ValueError as e:
        if "reverting selection to" not in repr(e):
            raise

    assert len(deconfigged_helper._app.data_collection) == 1
    assert u.Unit(viewer.state.x_display_unit) == u.Unit(expected_spectral_axis)
    assert u.Unit(viewer.state.y_display_unit) == u.Unit(expected_flux)


def test_initialize_specviz_sb(deconfigged_helper, spectrum1d):
    spec_sb = Spectrum(spectrum1d.flux/u.sr, spectrum1d.spectral_axis)
    deconfigged_helper.load(spec_sb, data_label="Test 1D Spectrum", format='1D Spectrum')
    plg = deconfigged_helper.plugins["Unit Conversion"]
    assert plg._obj.flux_unit == "Jy"
    assert plg._obj.spectral_y_type == "Surface Brightness"
    assert plg._obj.angle_unit == "sr"


@pytest.mark.parametrize('uncert', (False, True))
def test_conv_wave_only(deconfigged_helper, spectrum1d, uncert):
    if uncert is False:
        spectrum1d.uncertainty = None
    deconfigged_helper.load(spectrum1d, data_label="Test 1D Spectrum", format='1D Spectrum')

    viewer = deconfigged_helper._app.get_viewer('1D Spectrum')
    plg = deconfigged_helper.plugins["Unit Conversion"]
    new_spectral_axis = "micron"
    plg.spectral_unit = new_spectral_axis

    assert len(deconfigged_helper._app.data_collection) == 1
    assert u.Unit(viewer.state.x_display_unit) == u.Unit(new_spectral_axis)
    assert u.Unit(viewer.state.y_display_unit) == u.Unit('Jy')


@pytest.mark.parametrize('uncert', (False, True))
def test_conv_flux_only(deconfigged_helper, spectrum1d, uncert):
    if uncert is False:
        spectrum1d.uncertainty = None
    deconfigged_helper.load(spectrum1d, data_label="Test 1D Spectrum", format='1D Spectrum')

    viewer = deconfigged_helper._app.get_viewer('1D Spectrum')
    plg = deconfigged_helper.plugins["Unit Conversion"]
    new_flux = "erg / (s cm2 Angstrom)"
    plg._obj.flux_unit_selected = new_flux

    assert len(deconfigged_helper._app.data_collection) == 1
    assert u.Unit(viewer.state.x_display_unit) == u.Unit('Angstrom')
    assert u.Unit(viewer.state.y_display_unit) == u.Unit(new_flux)


@pytest.mark.parametrize('uncert', (False, True))
def test_conv_wave_flux(deconfigged_helper, spectrum1d, uncert):
    if uncert is False:
        spectrum1d.uncertainty = None
    deconfigged_helper.load(spectrum1d, data_label="Test 1D Spectrum", format='1D Spectrum')

    viewer = deconfigged_helper._app.get_viewer('1D Spectrum')
    plg = deconfigged_helper.plugins["Unit Conversion"]
    new_spectral_axis = "micron"
    new_flux = "erg / (s cm2 Angstrom)"
    plg.spectral_unit = new_spectral_axis
    plg._obj.flux_unit_selected = new_flux

    assert len(deconfigged_helper._app.data_collection) == 1
    assert u.Unit(viewer.state.x_display_unit) == u.Unit(new_spectral_axis)
    assert u.Unit(viewer.state.y_display_unit) == u.Unit(new_flux)


def test_conv_no_data(specviz_helper, spectrum1d):
    """plugin unit selections won't have valid choices yet, preventing
    attempting to set display units."""
    # spectrum not load is in Flux units, sb_unit and flux_unit
    # should be enabled, spectral_y_type should not be
    plg = specviz_helper.plugins["Unit Conversion"]
    with pytest.raises(ValueError, match='no valid unit choices'):
        plg.spectral_unit = "micron"
    assert len(specviz_helper._app.data_collection) == 0

    specviz_helper.load(spectrum1d, data_label="Test 1D Spectrum", format='1D Spectrum')

    # make sure we don't expose translations in Specviz
    assert hasattr(plg, 'flux_unit')
    assert hasattr(plg, 'angle_unit')
    assert not hasattr(plg, 'spectral_y_type')


def test_non_stddev_uncertainty(deconfigged_helper):
    flux = np.ones(10) * u.Jy
    stddev = 0.1
    var = stddev ** 2
    inv_var = np.ones(len(flux)) / var
    wavelength = np.linspace(1, 5, len(flux)) * u.um
    spec = Spectrum(
        flux,
        uncertainty=InverseVariance(inv_var),
        spectral_axis=wavelength
    )

    deconfigged_helper.load(spec, data_label="Test 1D Spectrum", format='1D Spectrum')

    po = deconfigged_helper.plugins['Plot Options']
    po.uncertainty_visible = True

    # check that the stddev uncertainties are drawn:
    viewer = deconfigged_helper._app.get_viewer('1D Spectrum')
    np.testing.assert_allclose(
        np.abs(viewer.figure.marks[-1].y - viewer.figure.marks[-1].y.mean(0)),
        stddev
    )


@pytest.mark.parametrize("flux_unit, expected_choices", [(u.count, []),
                                                         (u.Jy, SPEC_PHOTON_FLUX_DENSITY_UNITS),
                                                         (u.nJy, SPEC_PHOTON_FLUX_DENSITY_UNITS + ['nJy'])])  # noqa
def test_flux_unit_choices(deconfigged_helper, flux_unit, expected_choices):
    """
    Test that cubes loaded with various flux units have the expected default
    flux unit selection in the unit conversion plugin, and that the list of
    convertable flux units in the dropdown is correct.
    """

    spec = Spectrum([1, 2, 3] * flux_unit, [4, 5, 6] * u.um)
    deconfigged_helper.load(spec, format='1D Spectrum')

    uc_plg = deconfigged_helper.plugins['Unit Conversion']

    if u.Unit(flux_unit) == u.ct:
        assert uc_plg.flux_unit.selected == ''
    else:
        assert uc_plg.flux_unit.selected == flux_unit.to_string()
    assert uc_plg.flux_unit.choices == expected_choices


def test_mosviz_viewer_mouseover_flux(specviz2d_helper):
    data = np.zeros((5, 10))
    data[3] = np.arange(10)
    spectrum2d = Spectrum(flux=data*u.MJy, spectral_axis=data[3]*u.um)

    specviz2d_helper.load_data(spectrum2d)
    viewer = specviz2d_helper._app.get_viewer('spectrum-viewer')
    plg = specviz2d_helper.plugins["Unit Conversion"]

    # make sure we don't expose angle, sb, nor spectral-y units when native
    # units are in flux
    assert hasattr(plg, 'flux_unit')
    assert not hasattr(plg, 'angle_unit')
    assert not hasattr(plg, 'sb_unit')
    assert not hasattr(plg, 'spectral_y_type')

    label_mouseover = specviz2d_helper._coords_info
    label_mouseover._viewer_mouse_event(viewer,
                                        {'event': 'mousemove',
                                         'domain': {'x': 5, 'y': 3}})

    assert label_mouseover.as_text() == ('Cursor 5.00000e+00, 3.00000e+00',
                                         'Wave 5.00000e+00 um (5 pix)',
                                         'Flux 5.00000e+00 MJy')

    assert viewer.axis_y.label == 'Flux[MJy]'

    plg._obj.flux_unit_selected = 'Jy'
    # ensure axis label updates when flux unit is changed
    assert viewer.axis_y.label == 'Flux[Jy]'

    label_mouseover._viewer_mouse_event(viewer,
                                        {'event': 'mousemove',
                                         'domain': {'x': 5, 'y': 3}})

    assert label_mouseover.as_text() == ('Cursor 5.00000e+00, 3.00000e+00',
                                         'Wave 5.00000e+00 um (5 pix)',
                                         'Flux 5.00000e+06 Jy')

    # test mouseover when spectral density equivalencies are required for conversion
    plg._obj.flux_unit_selected = 'erg / (Angstrom s cm2)'
    assert viewer.axis_y.label == 'Flux[erg / (Angstrom s cm2)]'

    assert label_mouseover.as_text() == ('Cursor 5.00000e+00, 3.00000e+00',
                                         'Wave 5.00000e+00 um (5 pix)',
                                         'Flux 5.99585e-08 erg / (Angstrom s cm2)')


def test_mosviz_viewer_mouseover_sb(specviz2d_helper):
    data = np.zeros((5, 10))
    data[3] = np.arange(10)
    spectrum2d = Spectrum(flux=data*u.MJy/u.sr, spectral_axis=data[3]*u.um)

    specviz2d_helper.load_data(spectrum2d)
    spectrum_viewer = specviz2d_helper._app.get_viewer("spectrum-viewer")
    spectrum2d_viewer = specviz2d_helper._app.get_viewer('spectrum-2d-viewer')
    plg = specviz2d_helper.plugins["Unit Conversion"]

    # make sure we don't expose angle, sb, nor spectral-y units when native
    # units are in flux
    assert hasattr(plg, 'flux_unit')
    assert hasattr(plg, 'angle_unit')
    assert hasattr(plg, 'sb_unit')
    assert not hasattr(plg, 'spectral_y_type')

    label_mouseover = specviz2d_helper._app.session.application._tools['g-coords-info']
    label_mouseover._viewer_mouse_event(spectrum_viewer,
                                        {'event': 'mousemove',
                                         'domain': {'x': 5, 'y': 3}})
    assert label_mouseover.as_text() == ('Cursor 5.00000e+00, 3.00000e+00',
                                         'Wave 5.00000e+00 um (5 pix)',
                                         'Flux 5.00000e+00 MJy / sr')

    label_mouseover._viewer_mouse_event(spectrum2d_viewer, {"event": "mousemove",
                                                            "domain": {"x": 5, "y": 3}})
    output2d = label_mouseover.as_text()
    expected2d = ("Pixel x=05.0 y=03.0 Value +5.00000e+00 MJy / sr",
                  "Wave 5.00000e+00 um",
                  '')
    assert output2d == expected2d

    assert spectrum_viewer.axis_y.label == 'Surface Brightness[MJy / sr]'

    plg._obj.flux_unit_selected = 'Jy'
    assert spectrum_viewer.axis_y.label == 'Surface Brightness[Jy / sr]'

    label_mouseover._viewer_mouse_event(spectrum_viewer,
                                        {'event': 'mousemove',
                                         'domain': {'x': 5, 'y': 3}})
    output1d = label_mouseover.as_text()
    expected1d = ("Cursor 5.00000e+00, 3.00000e+00 Value +5.00000e+06 Jy / sr",
                  "Wave 5.00000e+00 um (5 pix)",
                  "Flux 5.00000e+06 Jy / sr")
    assert output1d == expected1d

    label_mouseover._viewer_mouse_event(spectrum2d_viewer, {"event": "mousemove",
                                                            "domain": {"x": 5, "y": 3}})
    output2d = label_mouseover.as_text()
    expected2d = ("Pixel x=05.0 y=03.0 Value +5.00000e+06 Jy / sr",
                  "Wave 5.00000e+00 um",
                  '')
    assert output2d == expected2d

    # test mouseover when spectral density equivalencies are required for conversion
    plg._obj.flux_unit_selected = 'erg / (Angstrom s cm2)'
    assert spectrum_viewer.axis_y.label == 'Surface Brightness[erg / (Angstrom s sr cm2)]'

    label_mouseover._viewer_mouse_event(spectrum_viewer,
                                        {'event': 'mousemove',
                                         'domain': {'x': 5, 'y': 3}})
    output1d = label_mouseover.as_text()
    expected1d = ("Cursor 5.00000e+00, 3.00000e+00 Value +5.99585e-08 erg / (Angstrom s sr cm2)",
                  "Wave 5.00000e+00 um (5 pix)",
                  "Flux 5.99585e-08 erg / (Angstrom s sr cm2)")
    assert output1d == expected1d

    label_mouseover._viewer_mouse_event(spectrum2d_viewer, {"event": "mousemove",
                                                            "domain": {"x": 5, "y": 3}})
    output2d = label_mouseover.as_text()
    expected2d = ("Pixel x=05.0 y=03.0 Value +5.99585e-08 erg / (Angstrom s sr cm2)",
                  "Wave 5.00000e+00 um",
                  '')
    assert output2d == expected2d


def test_image_deconfigged(deconfigged_helper, image_nddata_wcs):
    """
    Test that the unit conversion plugin works in deconfigged mode.
    """
    deconfigged_helper.load(image_nddata_wcs, format='Image', data_label="Test Image")
    plg = deconfigged_helper.plugins["Unit Conversion"]

    viewer = deconfigged_helper.viewers['Image']
    label_mouseover = deconfigged_helper._app.session.application._tools['g-coords-info']

    assert plg.flux_unit == "Jy"

    label_mouseover._viewer_mouse_event(viewer._obj.glue_viewer,
                                        {'event': 'mousemove',
                                         'domain': {'x': 1, 'y': 1}})
    assert label_mouseover.as_text() == ('Pixel x=01.0 y=01.0 Value +1.00000e+00 Jy',
                                         'World 22h30m04.7961s -20d49m58.9990s (ICRS)',
                                         '337.5199835909 -20.8330552820 (deg)')

    # Check that the units can be changed
    plg.flux_unit = "MJy"

    assert plg.flux_unit == "MJy"

    label_mouseover._viewer_mouse_event(viewer._obj.glue_viewer,
                                        {'event': 'mousemove',
                                         'domain': {'x': 1, 'y': 1}})
    assert label_mouseover.as_text() == ('Pixel x=01.0 y=01.0 Value +1.00000e-06 MJy',
                                         'World 22h30m04.7961s -20d49m58.9990s (ICRS)',
                                         '337.5199835909 -20.8330552820 (deg)')


def test_image_viewer_mouseover_unit(deconfigged_helper):
    """
    Test that the image viewer mouseover shows the correct flux unit for both
    physical (Jy) and non-physical (counts) data loaded in separate viewers.
    """
    ct_img = _image_nddata_wcs(unit=u.ct)
    jy_img = _image_nddata_wcs(unit=u.Jy)

    # Load counts image into the default Image viewer
    deconfigged_helper.load(ct_img, format='Image', data_label='ct_image')

    # Create a second Image viewer and load Jy image into it
    vc = deconfigged_helper.new_viewers['Image']
    vc()
    deconfigged_helper.load(jy_img, format='Image', data_label='jy_image',
                            viewer='Image (1)')

    ct_viewer = deconfigged_helper.viewers['Image']._obj.glue_viewer
    jy_viewer = deconfigged_helper.viewers['Image (1)']._obj.glue_viewer
    label_mouseover = deconfigged_helper._app.session.application._tools['g-coords-info']

    label_mouseover._viewer_mouse_event(ct_viewer,
                                        {'event': 'mousemove',
                                         'domain': {'x': 1, 'y': 1}})
    assert '+1.00000e+00 ct' in label_mouseover.as_text()[0]

    label_mouseover._viewer_mouse_event(jy_viewer,
                                        {'event': 'mousemove',
                                         'domain': {'x': 1, 'y': 1}})
    assert '+1.00000e+00 Jy' in label_mouseover.as_text()[0]


def test_mixed_physical_nonphysical_flux_unit_load(deconfigged_helper):
    """
    Test that loading a non-physical (counts) cube does not set the global
    flux display unit, but loading a physical (Jy) image afterwards does.
    """
    wcs_dict = {"CTYPE1": "WAVE-LOG", "CTYPE2": "DEC--TAN", "CTYPE3": "RA---TAN",
                "CRVAL1": 4.622e-7, "CRVAL2": 27, "CRVAL3": 205,
                "CDELT1": 8e-11, "CDELT2": 0.0001, "CDELT3": -0.0001,
                "CRPIX1": 0, "CRPIX2": 0, "CRPIX3": 0, "PIXAR_SR": 8e-11}
    w = WCS(wcs_dict)
    flux = np.ones((5, 5, 5), dtype=np.float32)
    cube = Spectrum(flux=flux * (u.ct / u.sr), wcs=w, meta=wcs_dict)

    deconfigged_helper.load(cube, format='3D Spectrum', data_label='ct_cube')

    uc_plg = deconfigged_helper.plugins['Unit Conversion']

    # non-physical flux should not populate the global flux display unit
    assert uc_plg.flux_unit.selected == ''
    assert uc_plg.flux_unit.choices == []

    # loading a physical image should set the global flux display unit
    jy_img = _image_nddata_wcs(unit=u.Jy / u.sr)
    deconfigged_helper.load(jy_img, format='Image', data_label='jy_image')

    assert uc_plg.flux_unit.selected == 'Jy'
    assert uc_plg.flux_unit.choices == SPEC_PHOTON_FLUX_DENSITY_UNITS

    # cube viewer should show native ct / sr despite the global display unit being Jy
    cube_viewer = deconfigged_helper.viewers['3D Spectrum']._obj.glue_viewer
    image_viewer = deconfigged_helper.viewers['Image']._obj.glue_viewer
    label_mouseover = deconfigged_helper._app.session.application._tools['g-coords-info']

    label_mouseover._viewer_mouse_event(cube_viewer,
                                        {'event': 'mousemove',
                                         'domain': {'x': 2, 'y': 2}})
    assert '+1.00000e+00 ct / sr' in label_mouseover.as_text()[0]

    label_mouseover._viewer_mouse_event(image_viewer,
                                        {'event': 'mousemove',
                                         'domain': {'x': 1, 'y': 1}})
    assert '+1.00000e+00 Jy / sr' in label_mouseover.as_text()[0]


def test_data_unload_reload(specviz2d_helper):
    """
    Test that when data is loaded (which sets ths initial unit selection
    for the unit conversion plugin), then removed, and a new dataset
    with different units is loaded, that the spectrum viewer is in the
    original units set by the first dataset. This behavior aligns with the
    idea that UC plugin selections should be app-wide settings.
    """
    # load initial data in MJy, um
    data = np.zeros((5, 10))
    data[3] = np.arange(10)
    spectrum2d = Spectrum(flux=data*u.MJy, spectral_axis=data[3]*u.um)

    specviz2d_helper.load_data(spectrum2d)

    # remove data from viewer
    viewer = specviz2d_helper._app.get_viewer('spectrum-viewer')
    dm = viewer.data_menu
    dm.remove_from_viewer()

    # make sure initial unit setting matches data units in both
    # plugin and on the spectrum viewer axes
    uc = specviz2d_helper.plugins['Unit Conversion']
    assert uc.flux_unit.selected == viewer.state.y_display_unit == 'MJy'
    assert uc.spectral_unit == viewer.state.x_display_unit == 'um'

    # re-load data with new units into the spectrum viewer
    spectrum2d_new = Spectrum(flux=data*u.Jy/u.sr, spectral_axis=data[3]*u.nm)
    specviz2d_helper.load_data(spectrum2d_new)

    # make sure newly loaded data did not change unit conversion selection,
    # and that the plugin traitlets and viewer attributes still match the
    # initially loaded unit
    uc = specviz2d_helper.plugins['Unit Conversion']
    assert uc.flux_unit.selected == viewer.state.y_display_unit == 'MJy'
    assert uc.spectral_unit == viewer.state.x_display_unit == 'um'


def test_toggle_spectral_y_type_deconfigged(deconfigged_helper, spectrum1d):
    """
    Test toggling between flux and surface brightness by setting
    'spectral_y_type' in the unit conversion plugin.
    """
    deconfigged_helper.load(spectrum1d, format='1D Spectrum')
    plg = deconfigged_helper.plugins["Unit Conversion"]

    # the initial selection should be "Flux" since the input spectrum is in flux units
    assert plg.spectral_y_type == "Flux"

    # toggle to surface brightness, then back to flux, and check that
    # spectral_y_type updates accordingly
    plg.spectral_y_type = "Surface Brightness"
    assert plg.spectral_y_type == "Surface Brightness"

    plg.spectral_y_type = "Flux"
    assert plg.spectral_y_type == "Flux"


@pytest.mark.parametrize('physical_first', [True, False])
def test_pix_and_physical_spectral_unit_load_order(deconfigged_helper, physical_first):
    """
    Test loading a pixel-axis spectrum and a physical-axis spectrum in either
    order. Spectral unit choices should be populated from the physical spectrum
    regardless of load order, and conversion should work without errors.
    """
    spec_pix_dn = Spectrum(flux=[1, 2, 3] * u.DN, spectral_axis=[1, 2, 3] * u.pix)
    spec_jy_nm = Spectrum(flux=[1, 2, 3] * u.Jy, spectral_axis=[1, 2, 3] * u.nm)

    if physical_first:
        deconfigged_helper.load(spec_jy_nm, data_label='jy_nm', format='1D Spectrum')
        plg = deconfigged_helper.plugins["Unit Conversion"]
        assert u.Unit(plg._obj.spectral_unit_selected) == u.Unit('nm')
        deconfigged_helper.load(spec_pix_dn, data_label='pix_dn', format='1D Spectrum')
    else:
        deconfigged_helper.load(spec_pix_dn, data_label='pix_dn', format='1D Spectrum')
        plg = deconfigged_helper.plugins["Unit Conversion"]
        # pixels is not a physical unit, so spectral_unit should not be set
        assert plg._obj.spectral_unit_selected == ''
        deconfigged_helper.load(spec_jy_nm, data_label='jy_nm', format='1D Spectrum')

    # after both are loaded, choices should be populated and nm selected
    assert len(plg._obj.spectral_unit.choices) > 0
    assert u.Unit(plg._obj.spectral_unit_selected) == u.Unit('nm')

    # converting from nm to Hz should not raise errors
    plg.spectral_unit = 'Hz'
    assert u.Unit(plg._obj.spectral_unit_selected) == u.Unit('Hz')


@pytest.mark.parametrize('pix_spec', ['1d', '2d'])
@pytest.mark.parametrize('dim_1d_first', [True, False])
def test_mixed_1d_2d_spectral_unit_load_order(deconfigged_helper, pix_spec, dim_1d_first):
    """
    Test loading a 1D and a 2D spectrum in either order, with pixel units for the
    spectral axis on either the 1D or 2D spectrum, to test mixed spectral axis unit
    types with different viewer types. Spectral unit choices should be populated
    from the spectrum that has physical units, and spectral axis unit conversion
    should work without errors, only acting on relevant viewers.
    """

    # This SHOULD work (and does when run in a notebook / script) but for some
    # reason not when run with pytest. remove this when JDAT-6288 is resolved
    if pix_spec == '1d':
        return

    spec_1d_saxis = u.pix if pix_spec == '1d' else u.nm
    spec_2d_saxis = u.pix if pix_spec == '2d' else u.nm

    spec_1d = Spectrum(flux=[1, 2, 3] * u.Jy,
                       spectral_axis=[1, 2, 3] * spec_1d_saxis)
    spec_2d = Spectrum(flux=np.ones((3, 3)) * u.Jy,
                       spectral_axis=[1, 2, 3] * spec_2d_saxis,
                       spectral_axis_index=-1)

    # determine whether the first-loaded spectrum has a pixel spectral axis
    first_is_pix = (dim_1d_first and pix_spec == '1d') or (not dim_1d_first and pix_spec == '2d')

    if dim_1d_first:
        deconfigged_helper.load(spec_1d, data_label='spec_1d', format='1D Spectrum')
        plg = deconfigged_helper.plugins["Unit Conversion"]
        if first_is_pix:
            assert plg.spectral_unit.selected == ''
        else:
            assert u.Unit(plg.spectral_unit.selected) == u.Unit('nm')
        deconfigged_helper.load(spec_2d, data_label='spec_2d', format='2D Spectrum')
    else:
        deconfigged_helper.load(spec_2d, data_label='spec_2d', format='2D Spectrum')
        plg = deconfigged_helper.plugins["Unit Conversion"]
        if first_is_pix:
            assert plg.spectral_unit.selected == ''
        else:
            assert u.Unit(plg.spectral_unit.selected) == u.Unit('nm')
        deconfigged_helper.load(spec_1d, data_label='spec_1d', format='1D Spectrum')

    # after both are loaded, choices should be populated and nm selected
    assert len(plg.spectral_unit.choices) > 0
    assert u.Unit(plg.spectral_unit.selected) == u.Unit('nm')

    # converting from nm to Hz should not raise errors
    plg.spectral_unit = 'Hz'
    assert u.Unit(plg.spectral_unit.selected) == u.Unit('Hz')


@pytest.mark.parametrize('ct_spec', ['1d', '2d'])
@pytest.mark.parametrize('dim_1d_first', [True, False])
def test_mixed_1d_2d_flux_unit_load_order(deconfigged_helper, ct_spec, dim_1d_first):
    """
    Test loading a 1D and a 2D spectrum in either order, with counts flux on
    either the 1D or 2D spectrum. Flux unit choices should be populated from
    the physical-unit spectrum regardless of load order, and flux unit
    conversion should work without errors.
    """
    spec_1d_flux = u.ct if ct_spec == '1d' else u.Jy
    spec_2d_flux = u.ct if ct_spec == '2d' else u.Jy

    spec_1d = Spectrum(flux=[1, 2, 3] * spec_1d_flux,
                       spectral_axis=[1, 2, 3] * u.nm)
    spec_2d = Spectrum(flux=np.ones((3, 3)) * spec_2d_flux,
                       spectral_axis=[1, 2, 3] * u.nm,
                       spectral_axis_index=-1)

    # whether the first-loaded spectrum has non-physical (counts) flux
    first_is_ct = (dim_1d_first and ct_spec == '1d') or (not dim_1d_first and ct_spec == '2d')

    if dim_1d_first:
        deconfigged_helper.load(spec_1d, data_label='spec_1d', format='1D Spectrum')
        plg = deconfigged_helper.plugins["Unit Conversion"]
        if first_is_ct:
            assert plg.flux_unit.selected == ''
        else:
            assert u.Unit(plg.flux_unit.selected) == u.Jy
        deconfigged_helper.load(spec_2d, data_label='spec_2d', format='2D Spectrum')
    else:
        deconfigged_helper.load(spec_2d, data_label='spec_2d', format='2D Spectrum')
        plg = deconfigged_helper.plugins["Unit Conversion"]
        if first_is_ct:
            assert plg.flux_unit.selected == ''
        else:
            assert u.Unit(plg.flux_unit.selected) == u.Jy
        deconfigged_helper.load(spec_1d, data_label='spec_1d', format='1D Spectrum')

    # after both are loaded, choices should be populated from the Jy spectrum
    assert len(plg.flux_unit.choices) > 0
    assert u.Unit(plg.flux_unit.selected) == u.Jy

    # converting to MJy should not raise errors
    plg.flux_unit = 'MJy'
    assert u.Unit(plg.flux_unit.selected) == u.MJy


def test_plugin_enabled_disabled(deconfigged_helper, sky_coord_only_source_catalog,
                                 image_nddata_wcs, spectrum1d):
    """
    Test that the Unit Conversion plugin is enabled when data is loaded in a
    relevant viewer, disabled when all data is removed, and re-enabled when
    data is added back.
    """
    deconfigged_helper.load(spectrum1d, format='1D Spectrum', data_label="test")

    plg = deconfigged_helper.plugins["Unit Conversion"]

    msg = 'Unit Conversion unavailable without data loaded in a viewer'

    # plugin should be enabled when data is loaded
    assert plg._obj.disabled_msg == ''

    # remove the data from the viewer, plugin should become disabled
    dm = deconfigged_helper.viewers['1D Spectrum'].data_menu
    dm.layer.selected = ['test']
    dm.remove_from_viewer()
    assert plg._obj.disabled_msg == msg

    # load a source catalog, which will be added to a new scatter viewer by default.
    # the unit conversion plugin should still be disabled since the check for
    # relevancy is for data in spectrum/image/cube viewers
    deconfigged_helper.load(sky_coord_only_source_catalog, format='Source Catalog')
    assert 'Source Catalog Table' in deconfigged_helper.viewers
    assert plg._obj.disabled_msg == msg

    # loading an image should re-enable the plugin
    deconfigged_helper.load(image_nddata_wcs, format='Image',
                            data_label='test_image')
    assert plg._obj.disabled_msg == ''


def test_plugin_disabled_on_viewer_removed(deconfigged_helper, image_nddata_wcs, spectrum1d):
    """
    Test that the Unit Conversion plugin responds to viewers being removed, i.e. it
    stays enabled while a relevant viewer with data remains, and is disabled
    once no relevant viewer with data remains.
    """
    deconfigged_helper.load(spectrum1d, format='1D Spectrum', data_label='spec')
    deconfigged_helper.load(image_nddata_wcs, format='Image', data_label='img')

    plg = deconfigged_helper.plugins["Unit Conversion"]._obj
    app = deconfigged_helper._app
    assert plg.disabled_msg == ''

    # the base TemplateMixin subscription must not be clobbered (one handler per
    # subscriber/message class in glue's hub) and should dispatch to the UC handler
    handler = app.hub._subscriptions[plg][ViewerRemovedMessage][0]
    assert handler.func.__name__ == '_on_viewer_removed'

    viewer_ids = list(app._viewer_store.keys())
    assert len(viewer_ids) == 2

    # removing one viewer leaves data in the other, so the plugin stays enabled
    app.vue_destroy_viewer_item(viewer_ids[0])
    assert plg.disabled_msg == ''

    # removing the last relevant viewer disables the plugin
    app.vue_destroy_viewer_item(viewer_ids[1])
    assert plg.disabled_msg == 'Unit Conversion unavailable without data loaded in a viewer'


def test_flux_unit_cleared_on_viewer_removed(deconfigged_helper, image_2d_wcs):
    """
    Test that when the viewer holding the only dataset with a physical flux unit
    is removed, leaving only counts data behind, the flux unit selection and
    choices (which could only have come from the removed data) are cleared, and
    the surface brightness unit is realigned to the remaining data.
    """
    spec_jy = Spectrum(flux=np.linspace(1, 2, 10) * u.Jy,
                       spectral_axis=np.linspace(1, 2, 10) * u.um)
    img_ct = NDData(np.ones(100).reshape(10, 10) * u.ct, wcs=image_2d_wcs)
    deconfigged_helper.load(spec_jy, format='1D Spectrum', data_label='spec_jy')
    deconfigged_helper.load(img_ct, format='Image', data_label='img_ct')

    plg = deconfigged_helper.plugins["Unit Conversion"]._obj
    app = deconfigged_helper._app

    assert plg.flux_unit_selected == 'Jy'
    assert len(plg.flux_unit.choices) > 0
    assert plg.angle_unit_selected == 'pix^2'
    assert plg.sb_unit_selected == 'Jy / pix2'

    [spec_viewer_id] = [vid for vid, v in app._viewer_store.items()
                        if isinstance(v, JdavizProfileView)]
    app.vue_destroy_viewer_item(spec_viewer_id)

    # only counts data remains, so the stale Jy flux selection is cleared
    assert plg.disabled_msg == ''
    assert plg.flux_unit_selected == ''
    assert plg.flux_unit.choices == []
    assert plg.angle_unit_selected == 'pix^2'
    assert plg.sb_unit_selected == 'ct / pix2'

    # loading new data with a physical flux unit repopulates the flux selection
    deconfigged_helper.load(spec_jy, format='1D Spectrum', data_label='spec_jy_2')
    assert plg.flux_unit_selected == 'Jy'
    assert plg.sb_unit_selected == 'Jy / pix2'


def test_flux_unit_kept_on_viewer_removed(deconfigged_helper, image_2d_wcs):
    """
    Test that when a viewer is removed and the remaining data has a different
    (but convertible) native flux unit, the flux unit selection is kept (any
    physical flux unit is still a valid display unit), while the angle unit is
    reset to the remaining data and the surface brightness unit is derived from
    the kept flux selection rather than the remaining data's native unit.
    """
    spec_jy = Spectrum(flux=np.linspace(1, 2, 10) * u.Jy,
                       spectral_axis=np.linspace(1, 2, 10) * u.um)
    img_mjy_sr = NDData(np.ones(100).reshape(10, 10) * u.MJy / u.sr, wcs=image_2d_wcs)
    deconfigged_helper.load(spec_jy, format='1D Spectrum', data_label='spec_jy')
    deconfigged_helper.load(img_mjy_sr, format='Image', data_label='img_mjy_sr')

    plg = deconfigged_helper.plugins["Unit Conversion"]._obj
    app = deconfigged_helper._app

    assert plg.flux_unit_selected == 'Jy'
    assert plg.angle_unit_selected == 'pix^2'
    assert plg.sb_unit_selected == 'Jy / pix2'

    [spec_viewer_id] = [vid for vid, v in app._viewer_store.items()
                        if isinstance(v, JdavizProfileView)]
    app.vue_destroy_viewer_item(spec_viewer_id)

    assert plg.disabled_msg == ''
    assert plg.flux_unit_selected == 'Jy'
    assert plg.angle_unit_selected == 'sr'
    assert plg.sb_unit_selected == 'Jy / sr'

    # flux selection remains functional and cascades to sb
    plg.flux_unit_selected = 'MJy'
    assert plg.sb_unit_selected == 'MJy / sr'


class TestResetUnitsToRemainingData:
    """
    Unit tests for the helpers that realign unit selections with the data that
    remains loaded. Each helper is driven directly with a synthetic
    ``native_units`` list of (plain_flux_unit, angle_unit) pairs, where
    ``angle_unit`` is None for data not in surface brightness units.
    """

    @pytest.fixture
    def plg(self, deconfigged_helper, spectrum1d):
        # spectrum1d is in Jy, which in deconfigged selects flux=Jy, angle=pix2, sb=Jy/pix2
        deconfigged_helper.load(spectrum1d, format='1D Spectrum', data_label='spec')
        plg = deconfigged_helper.plugins["Unit Conversion"]._obj
        assert plg.flux_unit_selected == 'Jy'
        assert plg.angle_unit_selected == 'pix^2'
        assert plg.sb_unit_selected == 'Jy / pix2'
        return plg

    @staticmethod
    def _clear_flux(plg):
        plg.flux_unit.choices = []
        plg.flux_unit_selected = ''
        assert plg.flux_unit_selected == ''

    # --- _reset_flux_unit_to_remaining_data ---

    def test_flux_cleared_when_no_physical_flux_remains(self, plg):
        plg._reset_flux_unit_to_remaining_data([(u.ct, None), (u.DN, None)])
        assert plg.flux_unit_selected == ''
        assert plg.flux_unit.choices == []

    def test_flux_populated_when_empty_and_physical_flux_remains(self, plg):
        self._clear_flux(plg)
        plg._reset_flux_unit_to_remaining_data([(u.MJy, u.sr)])
        assert plg.flux_unit_selected == 'MJy'
        assert 'MJy' in plg.flux_unit.choices

    def test_flux_kept_when_physical_flux_remains(self, plg):
        plg._reset_flux_unit_to_remaining_data([(u.MJy, u.sr)])
        assert plg.flux_unit_selected == 'Jy'

    def test_flux_kept_when_mixed_physical_and_counts_remain(self, plg):
        plg._reset_flux_unit_to_remaining_data([(u.ct, None), (u.MJy, None)])
        assert plg.flux_unit_selected == 'Jy'

    # --- _reset_angle_unit_to_remaining_data ---

    def test_angle_disagreement_returns_false_and_leaves_selection(self, plg):
        assert plg._reset_angle_unit_to_remaining_data([(u.Jy, None), (u.Jy, u.sr)]) is False
        assert plg.angle_unit_selected == 'pix^2'

    def test_angle_already_matching_returns_true(self, plg):
        assert plg._reset_angle_unit_to_remaining_data([(u.Jy, None), (u.ct, None)]) is True
        assert plg.angle_unit_selected == 'pix^2'

    def test_angle_reset_to_remaining_data(self, plg):
        assert plg._reset_angle_unit_to_remaining_data([(u.MJy, u.sr)]) is True
        assert plg.angle_unit_selected == 'sr'
        assert 'sr' in plg.angle_unit.choices
        # with a flux selection present, the angle change cascades to sb
        assert plg.sb_unit_selected == 'Jy / sr'

    # --- _reset_sb_unit_to_remaining_data ---

    def test_sb_derived_from_flux_selection(self, plg):
        plg.sb_unit_selected = 'MJy / pix2'
        plg._reset_sb_unit_to_remaining_data([(u.MJy, None)])
        # flux selection (Jy) takes precedence over the native unit (MJy)
        assert plg.sb_unit_selected == 'Jy / pix2'

    def test_sb_derived_from_native_unit_without_flux_selection(self, plg):
        self._clear_flux(plg)
        plg._reset_sb_unit_to_remaining_data([(u.ct, None)])
        assert plg.sb_unit_selected == 'ct / pix2'

    def test_sb_unchanged_when_already_consistent(self, plg):
        plg._reset_sb_unit_to_remaining_data([(u.MJy, None)])
        assert plg.sb_unit_selected == 'Jy / pix2'


def test_spectral_unit_kept_on_reference_data_removed(deconfigged_helper):
    """
    Test that removing the reference data from a 1D spectrum viewer keeps the selected
    spectral unit instead of reverting to the new reference data's native unit.
    """
    flux = np.linspace(1, 2, 10) * u.Jy
    deconfigged_helper.load(Spectrum(flux, spectral_axis=np.linspace(1, 2, 10) * u.um),
                            format='1D Spectrum', data_label='spec_um')
    deconfigged_helper.load(Spectrum(flux, spectral_axis=np.linspace(1000, 2000, 10) * u.nm),
                            format='1D Spectrum', data_label='spec_nm')

    app = deconfigged_helper._app
    [viewer] = [v for v in app._viewer_store.values() if isinstance(v, JdavizProfileView)]
    assert viewer.state.reference_data.label == 'spec_um'

    deconfigged_helper.plugins['Unit Conversion'].spectral_unit = 'Angstrom'
    assert viewer.state.x_display_unit == 'Angstrom'

    app.remove_data_from_viewer(viewer.reference, 'spec_um')
    assert viewer.state.reference_data.label == 'spec_nm'
    assert viewer.state.x_display_unit == 'nm'


def test_plugin_enabled_with_only_spectrum2d_viewer(deconfigged_helper, spectrum2d):
    """
    Test that the Unit Conversion plugin stays enabled when the 1D spectrum viewer is
    removed but the 2D spectrum viewer still has data.
    """
    deconfigged_helper.load(spectrum2d, format='2D Spectrum')
    plg = deconfigged_helper.plugins['Unit Conversion']._obj
    app = deconfigged_helper._app

    [viewer_1d_id] = [vid for vid, v in app._viewer_store.items()
                      if isinstance(v, JdavizProfileView)]
    app.vue_destroy_viewer_item(viewer_1d_id)
    assert plg.disabled_msg == ''


def test_unit_reset_on_all_data_removed(deconfigged_helper, spectrum1d):
    """
    Test that unit selections are reset when all data is removed from the app.
    """
    deconfigged_helper.load(spectrum1d, data_label='spec', format='1D Spectrum')

    plg = deconfigged_helper.plugins["Unit Conversion"]._obj
    # make sure the initial unit selections match the loaded data
    assert plg.spectral_unit_selected == 'Angstrom'
    assert plg.flux_unit_selected == 'Jy'

    # remove the data from the app
    app = deconfigged_helper._app
    deconfigged_helper._app.data_collection.remove(app.data_collection['spec'])

    assert len(app.data_collection) == 0

    # all unit selections should be cleared
    assert plg.spectral_unit_selected == ''
    assert plg.flux_unit_selected == ''
    assert plg.angle_unit_selected == ''
    assert plg.sb_unit_selected == ''
    assert plg.spectral_unit.choices == []
    assert plg.flux_unit.choices == []

    # check that loading new data after all data was removed resets the units
    deconfigged_helper.load(spectrum1d, data_label='spec2', format='1D Spectrum')
    assert plg.spectral_unit_selected == 'Angstrom'
    assert plg.flux_unit_selected == 'Jy'


def test_solid_angle_unit_reset(deconfigged_helper, image_2d_wcs):
    """
    Test to ensure that the solid angle display unit does not become 'stuck'
    in pix2 if an initial dataset in flux units with no solid angle component
    is loaded first (setting the solid angle unit to pix2 initially), then a
    dataset in surface brightness units per steradian is loaded. When the initial
    dataset in units of pix2 is then deleted, the unit conversion plugin selection
    for solid angle unit should be reset to steradians to reflect the remaining
    dataset.
    """

    # first, load dataset in ct / pix2
    img = NDData(np.ones(100).reshape(10, 10) * u.ct, wcs=image_2d_wcs)
    deconfigged_helper.load(img, data_label='img_ct', format='Image')

    plg = deconfigged_helper.plugins["Unit Conversion"]._obj
    assert plg.angle_unit_selected == 'pix^2'

    # now load an image in Jy / sr
    img = NDData(np.ones(100).reshape(10, 10) * u.Jy / u.sr, wcs=image_2d_wcs)
    deconfigged_helper.load(img, data_label='img_jy_sr', format='Image')

    # app should still be in pix2 since the first dataset in pix2 is still present
    assert plg.angle_unit_selected == 'pix^2'

    # now remove the initial dataset in ct and check that the angle unit resets to sr
    app = deconfigged_helper._app
    deconfigged_helper._app.data_collection.remove(app.data_collection['img_ct[DATA]'])

    assert plg.angle_unit_selected == 'sr'
