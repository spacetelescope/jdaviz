import numpy as np
import pytest
from astropy import units as u
from astropy.wcs import WCS
from regions import PixCoord, CirclePixelRegion
from specutils import Spectrum1D

from jdaviz.core.custom_units import PIX2
from jdaviz.core.validunits import locally_defined_flux_units


def cubeviz_wcs_dict():
    # returns a WCS obj and dictionary used for cubeviz tests
    wcs_dict = {"CTYPE1": "WAVE-LOG", "CTYPE2": "DEC--TAN", "CTYPE3": "RA---TAN",
                "CRVAL1": 4.622e-7, "CRVAL2": 27, "CRVAL3": 205,
                "CDELT1": 8e-11, "CDELT2": 0.0001, "CDELT3": -0.0001,
                "CRPIX1": 0, "CRPIX2": 0, "CRPIX3": 0, "PIXAR_SR": 8e-11}
    w = WCS(wcs_dict)
    return w, wcs_dict


@pytest.mark.skip(reason="Unskip after JDAT 4785 resolved.")
@pytest.mark.parametrize("angle_unit", [u.sr, PIX2])
def test_basic_unit_conversions(cubeviz_helper, angle_unit):
    """
    Basic test for changing flux units for a cube loaded in Jy to
    all available flux units. Checks that the the conversion does
    not produce any tracebacks. Tests conversions between all units
    in :
    ['Jy', 'mJy', 'uJy', 'MJy', 'W / (Hz m2)', 'eV / (Hz s m2)',
     'erg / (Hz s cm2)', 'erg / (Angstrom s cm2)',
     'ph / (Angstrom s cm2)', 'ph / (Hz s cm2)']

    Parametrized over both available solid angle units (pix2 and sr).
    """

    # load cube with flux units of MJy
    w, wcs_dict = cubeviz_wcs_dict()
    flux = np.zeros((30, 20, 3001), dtype=np.float32)
    cube = Spectrum1D(flux=flux * u.MJy / angle_unit, wcs=w, meta=wcs_dict)
    cubeviz_helper.load_data(cube, data_label="test")

    # get all available flux units for translation. Since cube is loaded
    # in Jy, this will be all items in 'locally_defined_flux_units'

    all_flux_units = locally_defined_flux_units()

    uc_plg = cubeviz_helper.plugins['Unit Conversion']

    for flux_unit in all_flux_units:
        uc_plg.flux_unit = flux_unit


@pytest.mark.parametrize("angle_unit", [u.sr, PIX2])
def test_unit_translation(cubeviz_helper, angle_unit):
    # custom cube so PIXAR_SR is in metadata, and Flux units, and in MJy
    w, wcs_dict = cubeviz_wcs_dict()
    flux = np.zeros((30, 20, 3001), dtype=np.float32)
    flux[5:15, 1:11, :] = 1
    cube = Spectrum1D(flux=flux * u.MJy / angle_unit, wcs=w, meta=wcs_dict)
    cubeviz_helper.load_data(cube, data_label="test")

    center = PixCoord(5, 10)
    cubeviz_helper.load_regions(CirclePixelRegion(center, radius=2.5))

    uc_plg = cubeviz_helper.plugins['Unit Conversion']

    # test that the scale factor was set
    assert np.all(cubeviz_helper.app.data_collection['Spectrum (sum)'].meta['_pixel_scale_factor'] != 1)  # noqa

    # When the dropdown is displayed, this ensures the loaded
    # data collection item units will be used for translations.
    assert uc_plg._obj.spectral_y_type_selected == 'Flux'

    # accessing from get_data(use_display_units=True) should return flux-like units
    assert cubeviz_helper.app._get_display_unit('spectral_y') == u.MJy
    assert cubeviz_helper.get_data('Spectrum (sum)', use_display_units=True).unit == u.MJy

    # to have access to display units
    viewer_1d = cubeviz_helper.app.get_viewer(
        cubeviz_helper._default_spectrum_viewer_reference_name)

    # change global y-units from Flux -> Surface Brightness
    uc_plg._obj.spectral_y_type_selected = 'Surface Brightness'

    assert uc_plg._obj.spectral_y_type_selected == 'Surface Brightness'
    y_display_unit = u.Unit(viewer_1d.state.y_display_unit)

    # check if units translated
    assert y_display_unit == u.MJy / angle_unit

    # get_data(use_display_units=True) should return surface brightness-like units
    assert cubeviz_helper.app._get_display_unit('spectral_y') == u.MJy / angle_unit
    assert cubeviz_helper.get_data('Spectrum (sum)', use_display_units=True).unit == u.MJy / angle_unit  # noqa


@pytest.mark.parametrize("angle_unit", [u.sr, PIX2])
def test_sb_unit_conversion(cubeviz_helper, angle_unit):

    angle_str = angle_unit.to_string()

    # custom cube to have Surface Brightness units
    w, wcs_dict = cubeviz_wcs_dict()
    flux = np.zeros((30, 20, 3001), dtype=np.float32)
    flux[5:15, 1:11, :] = 1
    cube = Spectrum1D(flux=flux * (u.MJy / angle_unit), wcs=w, meta=wcs_dict)
    cubeviz_helper.load_data(cube, data_label="test")

    uc_plg = cubeviz_helper.plugins['Unit Conversion']
    uc_plg.open_in_tray()

    # ensure that per solid angle cube defaults to Flux spectrum
    assert uc_plg.spectral_y_type == 'Flux'
    # flux choices is populated with flux units
    assert uc_plg.flux_unit.choices
    # and angle choices should be the only the input angle
    assert len(uc_plg.angle_unit.choices) == 1
    assert angle_str in uc_plg.angle_unit.choices

    # to have access to display units
    viewer_1d = cubeviz_helper.app.get_viewer(
        cubeviz_helper._default_spectrum_viewer_reference_name)

    uc_plg.spectral_y_type.selected = 'Surface Brightness'

    # Surface Brightness conversion
    uc_plg.flux_unit = 'Jy'
    y_display_unit = u.Unit(viewer_1d.state.y_display_unit)
    assert y_display_unit == u.Jy / angle_unit
    label_mouseover = cubeviz_helper.app.session.application._tools["g-coords-info"]
    flux_viewer = cubeviz_helper.app.get_viewer(
        cubeviz_helper._default_flux_viewer_reference_name
    )
    label_mouseover._viewer_mouse_event(
        flux_viewer, {"event": "mousemove", "domain": {"x": 10, "y": 8}}
    )
    assert label_mouseover.as_text() == (
            f"Pixel x=00010.0 y=00008.0 Value +1.00000e+06 Jy / {angle_str}",
            "World 13h39m59.7037s +27d00m03.2400s (ICRS)",
            "204.9987654313 27.0008999946 (deg)")

    # Try a second conversion
    uc_plg.flux_unit = 'W / Hz m2'

    if angle_unit == PIX2:  # unit string order is different for pix2 vs sr
        str_unit = 'W / (Hz m2 pix2)'
    elif angle_unit == u.sr:
        str_unit = 'W / (Hz sr m2)'

    y_display_unit = u.Unit(viewer_1d.state.y_display_unit)
    assert y_display_unit == u.Unit(str_unit)

    y_display_unit = u.Unit(viewer_1d.state.y_display_unit)
    label_mouseover._viewer_mouse_event(
        flux_viewer, {"event": "mousemove", "domain": {"x": 10, "y": 8}}
    )

    assert label_mouseover.as_text() == (
            f"Pixel x=00010.0 y=00008.0 Value +1.00000e-20 {str_unit}",
            "World 13h39m59.7037s +27d00m03.2400s (ICRS)",
            "204.9987654313 27.0008999946 (deg)")

    # really a translation test, test_unit_translation loads a Flux
    # cube, this test load a Surface Brightness Cube, this ensures
    # two-way translation
    uc_plg.flux_unit = 'MJy'
    y_display_unit = u.Unit(viewer_1d.state.y_display_unit)
    label_mouseover._viewer_mouse_event(
        flux_viewer, {"event": "mousemove", "domain": {"x": 10, "y": 8}}
    )
    assert label_mouseover.as_text() == (
            f"Pixel x=00010.0 y=00008.0 Value +1.00000e+00 MJy / {angle_str}",
            "World 13h39m59.7037s +27d00m03.2400s (ICRS)",
            "204.9987654313 27.0008999946 (deg)")

    uc_plg._obj.spectral_y_type_selected = 'Flux'
    uc_plg.flux_unit = 'Jy'
    y_display_unit = u.Unit(viewer_1d.state.y_display_unit)

    assert y_display_unit == u.Jy

    la = cubeviz_helper.plugins['Line Analysis']._obj
    assert la.dataset.get_selected_spectrum(use_display_units=True)


def test_contour_unit_conversion(cubeviz_helper, spectrum1d_cube_fluxunit_jy_per_steradian):
    # custom cube to have Surface Brightness units
    cubeviz_helper.load_data(spectrum1d_cube_fluxunit_jy_per_steradian, data_label="test")

    uc_plg = cubeviz_helper.plugins['Unit Conversion']
    uc_plg.open_in_tray()

    po_plg = cubeviz_helper.plugins['Plot Options']
    # Make sure that the contour values get updated
    po_plg.contour_visible = True

    assert uc_plg.spectral_y_type == 'Flux'
    assert uc_plg.flux_unit == 'Jy'
    assert uc_plg.sb_unit == "Jy / sr"
    assert cubeviz_helper.viewers['flux-viewer']._obj.layers[0].state.attribute_display_unit == "Jy / sr"  # noqa
    assert np.allclose(po_plg.contour_max.value, 199)

    uc_plg.spectral_y_type = 'Surface Brightness'
    uc_plg.flux_unit = 'MJy'

    assert uc_plg.sb_unit == "MJy / sr"
    assert cubeviz_helper.viewers['flux-viewer']._obj.layers[0].state.attribute_display_unit == "MJy / sr"  # noqa
    assert np.allclose(po_plg.contour_max.value, 1.99e-4)


@pytest.mark.parametrize("angle_unit", [u.sr, PIX2])
def test_cubeviz_flux_sb_translation_counts(cubeviz_helper, angle_unit):

    """
    When a cube is loaded in counts, 'count' should be the only
    available option for flux unit. The y axis can be translated
    between flux and sb. Test a flux cube which will be converted
    to ct/pix2, and a sb cube ct/sr.
    """

    angle_str = angle_unit.to_string()

    # custom cube to have Surface Brightness units
    w, wcs_dict = cubeviz_wcs_dict()
    flux = np.zeros((30, 20, 3001), dtype=np.float32)
    flux[5:15, 1:11, :] = 1
    cube = Spectrum1D(flux=flux * (u.ct / angle_unit), wcs=w, meta=wcs_dict)
    cubeviz_helper.load_data(cube, data_label="test")

    uc_plg = cubeviz_helper.plugins['Unit Conversion']
    uc_plg.open_in_tray()

    # ensure that per solid angle cube defaults to Flux spectrum
    assert uc_plg.spectral_y_type == 'Flux'
    # flux choices is populated with only one choice, counts
    assert len(uc_plg.flux_unit.choices) == 1
    assert 'ct' in uc_plg.flux_unit.choices
    # and angle choices should be the only the input angle
    assert len(uc_plg.angle_unit.choices) == 1
    assert angle_str in uc_plg.angle_unit.choices

    # to have access to display units
    viewer_1d = cubeviz_helper.app.get_viewer(
        cubeviz_helper._default_spectrum_viewer_reference_name)

    # do a spectral y axis translation from Flux to Surface Brightness
    uc_plg.spectral_y_type.selected = 'Surface Brightness'

    y_display_unit = u.Unit(viewer_1d.state.y_display_unit)
    assert y_display_unit == u.ct / angle_unit

    # and test mouseover info
    label_mouseover = cubeviz_helper.app.session.application._tools["g-coords-info"]
    flux_viewer = cubeviz_helper.app.get_viewer(
        cubeviz_helper._default_flux_viewer_reference_name
    )
    label_mouseover._viewer_mouse_event(
        flux_viewer, {"event": "mousemove", "domain": {"x": 10, "y": 8}}
    )
    assert label_mouseover.as_text() == (
            f"Pixel x=00010.0 y=00008.0 Value +1.00000e+00 ct / {angle_str}",
            "World 13h39m59.7037s +27d00m03.2400s (ICRS)",
            "204.9987654313 27.0008999946 (deg)")
