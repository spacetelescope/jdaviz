import numpy as np
import astropy.units as u
from astropy.modeling.fitting import LevMarLSQFitter
from astropy.modeling.models import Gaussian1D
from astropy.tests.helper import assert_quantity_allclose
from specutils import Spectrum


def test_cross_dispersion_profile(specviz2d_helper):
    """Tests the basic functionality of the cross dispersion profile plugin."""

    # Create a 2D array representing a series of Gaussian profiles.
    # Each column i corresponds to a Gaussian centered at y=5 with amplitude=i.
    # The amplitude increases along the spectral axis
    x = np.arange(25)
    y = np.arange(10)
    arr = np.zeros((10, 25))
    for i in range(25):
        arr[:, i] = Gaussian1D(amplitude=i, mean=5, stddev=1)(y)

    data = Spectrum(flux=arr * u.Jy, spectral_axis=x * u.nm)
    specviz2d_helper.load_data(data)

    cdp = specviz2d_helper.plugins['Cross Dispersion Profile']
    cdp.open_in_tray()

    fitter = LevMarLSQFitter()
    model = Gaussian1D()

    # check defaults
    assert cdp.pixel == 12
    assert cdp.use_full_width
    assert cdp.width == 10
    assert cdp.y_pixel == 5

    # check that 2d spectrum viewer marks marks (vertical line with scatter)
    # are in the correct starting location
    assert np.all(cdp._obj.marks['2d']['pix'].x == 12)
    assert np.all(cdp._obj.marks['2d']['y_pix'].y == 5)

    # make sure the profile at row 12 is a gaussian with amp. 12, as the test
    # data was designed
    fit = fitter(model, y, cdp.profile)
    assert fit.amplitude == 12 * u.Jy
    assert fit.mean == 5

    # now move the pixel slider to col 13 and make sure the fit profile
    # now reflects a gaussian with amplitude 13, and that the plugin marks
    # have moved as well
    cdp.pixel = 13
    profile_13 = cdp.profile
    fit = fitter(model, y, profile_13)
    assert fit.amplitude == 13 * u.Jy
    assert fit.mean == 5
    assert np.all(cdp._obj.marks['2d']['pix'].x == 13)
    assert np.all(cdp._obj.marks['2d']['y_pix'].y == 5)

    # and now adjust the width, and make sure the profile and
    # marks changed accordingly
    cdp.use_full_width = False
    cdp.width = 5
    assert len(cdp.profile) == 5
    assert len(cdp._obj.marks['2d']['pix'].y) == 5
    cdp.width = 7
    prev_profile = cdp.profile  # save profile to compare after unit conversions
    assert len(cdp.profile) == 7
    assert len(cdp._obj.marks['2d']['pix'].y) == 7

    # test flux unit conversion
    uc = specviz2d_helper.plugins['Unit Conversion']
    uc.flux_unit.selected = 'MJy'
    assert cdp.profile.unit == u.MJy
    # convert profile saved at the step above to new
    # unit to make sure it was converted
    assert_quantity_allclose(prev_profile, cdp.profile)

    # test flux unit conversion that needs an equivalency
    uc = specviz2d_helper.plugins['Unit Conversion']
    uc.flux_unit.selected = 'erg / (Angstrom s cm2)'
    un = u.Unit('erg / (Angstrom s cm2)')
    assert cdp.profile.unit == un
    # convert before comparing since we need an equivalency based on the wavelength
    eqv = u.spectral_density(cdp._obj.wav * u.Unit(cdp._obj.sa_display_unit))
    converted = cdp.profile.to(u.Jy, eqv)
    assert_quantity_allclose(prev_profile, converted)

    # do a spectral axis conversion and make sure the plot title updated
    # to reflect the new wavelength
    uc.spectral_unit.selected = 'nm'
    assert 'nm' in cdp._obj.plot.figure.title

    # todo: add tests to cover selecting new datasets (e.g background image
    # from the spectral extraction plugin) once JDAT-5426 is resolved. need
    # to test that dataset_selected behaves correctly
