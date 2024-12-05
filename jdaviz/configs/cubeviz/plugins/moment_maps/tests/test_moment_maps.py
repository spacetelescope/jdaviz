import warnings
from pathlib import Path

import numpy as np
import pytest
from astropy import units as u
from astropy.nddata import CCDData
from astropy.tests.helper import assert_quantity_allclose
from astropy.wcs import WCS
from numpy.testing import assert_allclose
from specutils import SpectralRegion

from jdaviz.core.custom_units_and_equivs import PIX2, SPEC_PHOTON_FLUX_DENSITY_UNITS


@pytest.mark.parametrize("cube_type", ["Surface Brightness", "Flux"])
def test_user_api(cubeviz_helper, spectrum1d_cube, spectrum1d_cube_sb_unit, cube_type):

    # test is parameterize to test a cube that is in Jy / sr (Surface Brightness)
    # as well as Jy (Flux), to test that flux cubes, which are converted in the
    # parser to flux / pix^2 surface brightness cubes, both work correctly.

    if cube_type == 'Surface Brightness':
        cube = spectrum1d_cube_sb_unit
    elif cube_type == 'Flux':
        cube = spectrum1d_cube

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="No observer defined on WCS.*")
        cubeviz_helper.load_data(cube, data_label='test')

    mm = cubeviz_helper.plugins['Moment Maps']
    assert not mm._obj.continuum_marks['center'].visible
    with mm.as_active():
        assert mm._obj.continuum_marks['center'].visible
        mm.n_moment = 0
        # no continuum so marks should be empty
        assert len(mm._obj.continuum_marks['center'].x) == 0

        mom = mm.calculate_moment()

        mm.continuum = 'Surrounding'
        mm.continuum_width = 10
        assert len(mm._obj.continuum_marks['center'].x) > 0

        mom_sub = mm.calculate_moment()
        assert isinstance(mom_sub.wcs, WCS)

        assert mom != mom_sub

        mm.n_moment = -1
        with pytest.raises(ValueError, match="Moment must be a positive integer"):
            mm.calculate_moment()

        mm.n_moment = 1
        with pytest.raises(ValueError, match="not one of"):
            mm._obj.output_unit_selected = "Bad Unit"
        mm._obj.output_unit_selected = "Surface Brightness"
        with pytest.raises(ValueError, match="units must be in"):
            mm.calculate_moment()


@pytest.mark.parametrize("cube_type", ["Surface Brightness", "Flux"])
def test_moment_calculation(cubeviz_helper, spectrum1d_cube,
                            spectrum1d_cube_sb_unit, cube_type, tmp_path):

    moment_unit = "Jy m"
    moment_value_str = "+6.40166e-10"

    if cube_type == 'Surface Brightness':
        moment_unit += " / sr"
        cube = spectrum1d_cube_sb_unit
        cube_unit = cube.unit.to_string()

    elif cube_type == 'Flux':
        moment_unit += " / pix2"
        cube = spectrum1d_cube
        cube_unit = cube.unit.to_string() + " / pix2"  # cube in Jy will become cube in Jy / pix2

    dc = cubeviz_helper.app.data_collection
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="No observer defined on WCS.*")
        cubeviz_helper.load_data(cube, data_label='test')

    flux_viewer = cubeviz_helper.app.get_viewer(cubeviz_helper._default_flux_viewer_reference_name)

    # Since we are not really displaying, need this to trigger GUI stuff.
    flux_viewer.shape = (100, 100)
    flux_viewer.state._set_axes_aspect_ratio(1)

    mm = cubeviz_helper.plugins["Moment Maps"]
    mm.dataset = 'test[FLUX]'

    mm.n_moment = 0  # Collapsed sum, will get back 2D spatial image
    assert mm._obj.results_label == 'moment 0'

    # result is always a SB unit - if flux cube loaded, per pix2
    assert mm.output_unit == 'Surface Brightness'

    mm._obj.add_results.viewer.selected = cubeviz_helper._default_uncert_viewer_reference_name
    mm._obj.vue_calculate_moment()

    assert mm._obj.moment_available
    assert dc[-1].label == 'moment 0'
    mv_data = cubeviz_helper.app.get_viewer(
        cubeviz_helper._default_uncert_viewer_reference_name
    ).data()
    # by default, will overwrite the previous entry (so only one data entry)
    assert len(mv_data) == 1
    assert mv_data[0].label == 'moment 0'

    assert len(dc.links) == 19

    # label should remain unchanged but raise overwrite warnings
    assert mm._obj.results_label == 'moment 0'
    assert mm._obj.results_label_overwrite is True

    # Make sure coordinate display works in flux viewer (loaded data, not the moment map)
    label_mouseover = cubeviz_helper.app.session.application._tools['g-coords-info']
    label_mouseover._viewer_mouse_event(flux_viewer, {'event': 'mousemove',
                                                      'domain': {'x': 0, 'y': 0}})
    assert flux_viewer.state.slices == (0, 0, 1)
    # Slice 0 has 8 pixels, this is Slice 1
    assert label_mouseover.as_text() == (f"Pixel x=00.0 y=00.0 Value +8.00000e+00 {cube_unit}",
                                         "World 13h39m59.9731s +27d00m00.3600s (ICRS)",
                                         "204.9998877673 27.0001000000 (deg)")

    # Make sure adding it to viewer does not crash.
    cubeviz_helper.app.add_data_to_viewer(
        cubeviz_helper._default_flux_viewer_reference_name, 'moment 0'
    )

    result = dc[-1].get_object(cls=CCDData)
    assert result.shape == (2, 4)  # Cube shape is (2, 2, 4), moment transposes
    assert isinstance(dc[-1].coords, WCS)

    # Make sure coordinate display now show moment map info (no WCS)
    label_mouseover._viewer_mouse_event(flux_viewer, {'event': 'mousemove',
                                                      'domain': {'x': 0, 'y': 0}})

    # Slice 0 has 8 pixels, this is Slice 1
    assert label_mouseover.as_text() == (
        f"Pixel x=00.0 y=00.0 Value {moment_value_str} {moment_unit}",
        "World 13h39m59.9731s +27d00m00.3600s (ICRS)",
        "204.9998877673 27.0001000000 (deg)")

    mm._obj.n_moment = 1
    mm._obj.output_unit_selected = "Spectral Unit"
    assert mm._obj.results_label == 'moment 1'
    assert mm._obj.results_label_overwrite is False
    mm._obj.vue_calculate_moment()

    assert dc[-1].label == 'moment 1'

    assert len(dc.links) == 27
    assert len(dc.external_links) == 6  # pixel linked
    # Link 3D z to 2D x and 3D y to 2D y
    assert (dc.external_links[2].cids1[0].label == "Pixel Axis 0 [z]" and
            dc.external_links[2].cids2[0].label == "Pixel Axis 1 [x]" and
            dc.external_links[3].cids1[0].label == "Pixel Axis 1 [y]" and
            dc.external_links[3].cids2[0].label == "Pixel Axis 0 [y]")

    # Coordinate display should be unaffected.
    label_mouseover._viewer_mouse_event(flux_viewer, {'event': 'mousemove',
                                                      'domain': {'x': 0, 'y': 0}})
    assert label_mouseover.as_text() == (
        f"Pixel x=00.0 y=00.0 Value {moment_value_str} {moment_unit}",
        "World 13h39m59.9731s +27d00m00.3600s (ICRS)",
        "204.9998877673 27.0001000000 (deg)")


def test_moment_velocity_calculation(cubeviz_helper, spectrum1d_cube):
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="No observer defined on WCS.*")
        cubeviz_helper.load_data(spectrum1d_cube, data_label='test')

    uncert_viewer = cubeviz_helper.app.get_viewer("uncert-viewer")

    # Since we are not really displaying, need this to trigger GUI stuff.
    uncert_viewer.shape = (100, 100)
    uncert_viewer.state._set_axes_aspect_ratio(1)

    mm = cubeviz_helper.plugins["Moment Maps"]
    mm._obj.dataset_selected = 'test[FLUX]'

    # Test moment 1 in velocity
    mm.n_moment = 1
    mm.add_results.viewer = "uncert-viewer"
    assert mm._obj.results_label == 'moment 1'
    mm.output_unit = "Velocity"

    with pytest.raises(ValueError, match="reference_wavelength must be set"):
        mm.calculate_moment()

    mm.reference_wavelength = 4.63e-7
    mm.calculate_moment()

    # Make sure coordinate display works
    label_mouseover = cubeviz_helper.app.session.application._tools['g-coords-info']
    label_mouseover._viewer_mouse_event(uncert_viewer, {'event': 'mousemove',
                                                        'domain': {'x': 0, 'y': 0}})
    assert label_mouseover.as_text() == ("Pixel x=00.0 y=00.0 Value -4.14668e+02 km / s",
                                         "World 13h39m59.9731s +27d00m00.3600s (ICRS)",
                                         "204.9998877673 27.0001000000 (deg)")

    # Add test for unit conversion
    assert mm._obj.output_radio_items[0]['unit_str'] == 'm'
    uc_plugin = cubeviz_helper.plugins['Unit Conversion']._obj
    uc_plugin.spectral_unit.selected = 'Angstrom'
    assert mm._obj.output_radio_items[0]['unit_str'] == 'Angstrom'
    uc_plugin.spectral_unit.selected = 'm'

    # Test moment 2 in velocity
    mm.n_moment = 2
    mm.calculate_moment()

    label_mouseover._viewer_mouse_event(uncert_viewer, {'event': 'mousemove',
                                                        'domain': {'x': 1, 'y': 1}})

    assert label_mouseover.as_text() == ("Pixel x=01.0 y=01.0 Value +2.32415e+01 km / s",
                                         "World 13h39m59.9461s +27d00m00.7200s (ICRS)",
                                         "204.9997755344 27.0001999998 (deg)")


def test_moment_frequency_unit_conversion(cubeviz_helper, spectrum1d_cube_larger):
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="No observer defined on WCS.*")
        cubeviz_helper.load_data(spectrum1d_cube_larger, data_label='test')

    uc = cubeviz_helper.plugins['Unit Conversion']
    mm = cubeviz_helper.plugins['Moment Maps']

    unit = u.Unit(uc.spectral_unit.selected)
    cubeviz_helper.plugins['Subset Tools'].import_region(
        SpectralRegion(4.624e-07 * unit, 4.627e-07 * unit))

    uc.spectral_unit = 'Hz'
    mm.spectral_subset = 'Subset 1'
    mm.continuum = 'Surrounding'
    mm.n_moment = 1
    mm.output_unit = 'Spectral Unit'
    moment_1_data = mm.calculate_moment()
    mm.n_moment = 0
    moment_0_data = mm.calculate_moment()

    # Check to make sure there are no nans
    assert len(np.where(moment_1_data.data > 0)[0]) == 8
    assert_quantity_allclose(moment_0_data, -2.9607526e+09*u.Unit("Hz Jy / pix2"))


def test_write_momentmap(cubeviz_helper, spectrum1d_cube, tmp_path):
    ''' Test writing a moment map out to a FITS file on disk '''

    # Simulate an existing file on disk to check for overwrite warning
    test_file = tmp_path / "test_file.fits"
    existing_sentinel_text = "This is a simulated, existing file on disk"
    test_file.write_text(existing_sentinel_text)

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="No observer defined on WCS.*")
        cubeviz_helper.load_data(spectrum1d_cube, data_label='test')
    plugin = cubeviz_helper.plugins['Moment Maps']
    plugin.calculate_moment()

    # and shouldn't have written anything (the file should be intact)
    assert test_file.read_text() == existing_sentinel_text

    label = plugin._obj.add_results.label
    export_plugin = cubeviz_helper.plugins['Export']._obj

    assert label in export_plugin.data_collection.labels


@pytest.mark.remote_data
def test_momentmap_nirspec_prism(cubeviz_helper, tmp_path):
    uri = "mast:jwst/product/jw02732-o003_t002_nirspec_prism-clear_s3d.fits"
    local_path = str(tmp_path / Path(uri).name)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cubeviz_helper.load_data(uri, cache=True, local_path=local_path)
    uc = cubeviz_helper.plugins["Unit Conversion"]
    uc.open_in_tray()  # plugin has to be open for unit change to take hold
    uc._obj.show_translator = True
    uc.spectral_y_type.selected = 'Surface Brightness'
    mm = cubeviz_helper.plugins['Moment Maps']._obj
    mm.open_in_tray()  # plugin has to be open for unit change to take hold
    mm._set_data_units()
    mm.calculate_moment()
    assert isinstance(mm.moment.wcs, WCS)

    # Because cube axes order is re-arranged by specutils on load, this gets confusing.
    # There is a swapaxes within Moment Map WCS calculation.
    sky_moment = mm.moment.wcs.pixel_to_world(50, 30)
    sky_cube = cubeviz_helper.app.data_collection[0].meta["_orig_spec"].wcs.celestial.pixel_to_world(30, 50)  # noqa: E501
    assert_allclose((sky_moment.ra.deg, sky_moment.dec.deg),
                    (sky_cube.ra.deg, sky_cube.dec.deg))


def test_correct_output_spectral_y_units(cubeviz_helper, spectrum1d_cube_custom_fluxunit):

    moment_unit = "Jy m / sr"

    # test that the output unit labels in the moment map plugin reflect any
    # changes made in the unit conversion plugin.
    # NOTE: for now this is limited to moment 0, test should be expanded to
    # test higher-order moments once implemented.

    sb_cube = spectrum1d_cube_custom_fluxunit(fluxunit=u.MJy / u.sr)

    # load surface brigtness cube
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="No observer defined on WCS.*")
        cubeviz_helper.load_data(sb_cube, data_label='test')

    uc = cubeviz_helper.plugins["Unit Conversion"]
    uc.open_in_tray()  # plugin has to be open for unit change to take hold
    uc._obj.show_translator = True
    uc.spectral_y_type.selected = 'Surface Brightness'
    mm = cubeviz_helper.plugins['Moment Maps']._obj
    mm.open_in_tray()  # plugin has to be open for unit change to take hold
    mm._set_data_units()

    # check that label is initialized with 'Surface Brightness' since the cube
    # loaded is in MJy / sr. for the 0th moment, the only item will be the 0th
    # in this list. also check that the initial unit is correct.
    output_unit_moment_0 = mm.output_unit_items[0]
    assert output_unit_moment_0['label'] == 'Surface Brightness'
    assert output_unit_moment_0['unit_str'] == 'MJy m / sr'

    # check that calculated moment has the correct units of MJy m / sr
    mm.calculate_moment()
    assert mm.moment.unit == f'M{moment_unit}'

    # now change surface brightness units in the unit conversion plugin

    uc.flux_unit = 'Jy'

    # and make sure this change is propogated
    output_unit_moment_0 = mm.output_unit_items[0]
    assert output_unit_moment_0['label'] == 'Surface Brightness'
    assert output_unit_moment_0['unit_str'] == 'Jy m / sr'

    # and that calculated moment has the correct units
    mm.calculate_moment()
    assert mm.moment.unit == moment_unit

    # now change the spectral unit and make sure that change is
    # reflected in MM plugin
    uc.spectral_unit = 'um'
    assert output_unit_moment_0['unit_str'] == 'Jy um / sr'

    mm.calculate_moment()
    assert mm.moment.unit == moment_unit.replace('m', 'um')


@pytest.mark.parametrize("flux_unit", [u.Unit(x) for x in SPEC_PHOTON_FLUX_DENSITY_UNITS][1:2])
@pytest.mark.parametrize("angle_unit", [u.sr, PIX2])
@pytest.mark.parametrize("new_flux_unit", [u.Unit(x) for x in SPEC_PHOTON_FLUX_DENSITY_UNITS][1:2])
def test_moment_zero_unit_flux_conversions(cubeviz_helper,
                                           spectrum1d_cube_custom_fluxunit,
                                           flux_unit, angle_unit, new_flux_unit):
    """
    Test cubeviz moment maps with all possible unit conversions for
    cubes in spectral/photon surface brightness units (e.g. Jy/sr, Jy/pix2).

    The moment map plugin should respect the choice of flux and angle
    unit selected in the Unit Conversion plugin, and inputs and results should
    be converted based on selection. All conversions between units in the
    flux dropdown menu in the unit conversion plugin should be supported
    by moment maps.
    """

    if new_flux_unit == flux_unit:  # skip 'converting' to same unit
        return
    new_flux_unit_str = new_flux_unit.to_string()

    cube_unit = flux_unit / angle_unit

    sb_cube = spectrum1d_cube_custom_fluxunit(fluxunit=cube_unit)

    # load surface brigtness cube
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="No observer defined on WCS.*")
        cubeviz_helper.load_data(sb_cube, data_label='test')

    # get plugins
    uc = cubeviz_helper.plugins["Unit Conversion"]
    mm = cubeviz_helper.plugins['Moment Maps']._obj

    # and flux viewer for mouseover info
    flux_viewer = cubeviz_helper.app.get_viewer(cubeviz_helper._default_flux_viewer_reference_name)
    label_mouseover = cubeviz_helper.app.session.application._tools['g-coords-info']

    # convert to new flux unit
    uc.flux_unit.selected = new_flux_unit_str

    new_mm_unit = (new_flux_unit * u.m / u.Unit(angle_unit)).to_string()
    assert mm.output_unit_items[0]['label'] == 'Surface Brightness'
    assert mm.output_unit_items[0]['unit_str'] == new_mm_unit

    # calculate moment with new output label and plot in flux viewer
    mm.add_results.label = new_flux_unit_str
    mm.add_results.viewer.selected = cubeviz_helper._default_flux_viewer_reference_name
    mm.calculate_moment()

    assert mm.moment.unit == new_mm_unit

    # make sure mouseover info in flux unit is new moment map unit
    # which should be flux/sb unit times spectral axis unit (e.g. MJy m / sr)
    label_mouseover._viewer_mouse_event(flux_viewer,
                                        {'event': 'mousemove',
                                         'domain': {'x': 0, 'y': 0}})
    m_orig = label_mouseover.as_text()[0]
    assert ((new_flux_unit / angle_unit) * u.m).to_string() in m_orig

    # 'jiggle' mouse so we can move it back and compare original coordinate
    label_mouseover._viewer_mouse_event(flux_viewer,
                                        {'event': 'mousemove',
                                         'domain': {'x': 1, 'y': 1}})

    # when flux unit is changed, the mouseover unit conversion should be
    # skipped so that the plotted moment map remains in its original
    # unit. setting back to the original flux unit also ensures that
    # each iteration begins on the same unit so that every comparison
    # is tested
    uc.flux_unit.selected = new_flux_unit_str
    label_mouseover._viewer_mouse_event(flux_viewer,
                                        {'event': 'mousemove',
                                         'domain': {'x': 0, 'y': 0}})
    assert m_orig == label_mouseover.as_text()[0]
