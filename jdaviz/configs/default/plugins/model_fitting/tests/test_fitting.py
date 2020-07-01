import astropy.modeling.models as models
import astropy.units as u
import numpy as np
from specutils.spectra import Spectrum1D

from .. import fitting_backend as fb


SPECTRUM_SIZE = 200 # length of spectrum
IMAGE_SIZE    =  15 # size of slab (IMAGE_SIZE x IMAGE_SIZE spaxels)


def build_spectrum(sigma=0.1):
    g1 = models.Gaussian1D(1, 4.6, 0.2)
    g2 = models.Gaussian1D(2.5, 5.5, 0.1)
    g3 = models.Gaussian1D(-1.7, 8.2, 0.1)

    x = np.linspace(0, 10, SPECTRUM_SIZE)
    y = g1(x) + g2(x) + g3(x)

    noise = np.random.normal(4., sigma, x.shape)

    return x, y + noise


def test_fitting_backend():
    np.random.seed(42)

    x, y = build_spectrum()

    spectrum = Spectrum1D(flux=y*u.Jy, spectral_axis=x*u.um)

    g1f = models.Gaussian1D(0.7*u.Jy, 4.65*u.um, 0.3*u.um, name='g1')
    g2f = models.Gaussian1D(2.0*u.Jy, 5.55*u.um, 0.3*u.um, name='g2')
    g3f = models.Gaussian1D(-2.*u.Jy, 8.15*u.um, 0.2*u.um, name='g3')
    zero_level = models.Const1D(1.*u.Jy, name='const1d')

    model_list = [g1f, g2f, g3f, zero_level]
    expression = "g1 + g2 + g3 + const1d"

    # Returns the intial model
    fm, fitted_spectrum = fb.fit_model_to_spectrum(spectrum, model_list, expression, run_fitter=False)

    parameters_expected = np.array([0.7,4.65,0.3,2.,5.55,0.3,-2.,8.15,0.2,1.])
    assert np.allclose(fm.parameters, parameters_expected, atol=1e-5)

    # Returns the fitted model
    fm, fitted_spectrum = fb.fit_model_to_spectrum(spectrum, model_list, expression, run_fitter=True)

    parameters_expected = np.array([1.0104705, 4.58956282, 0.19590464, 2.39892026,
                                    5.49867754, 0.10834472, -1.66902953, 8.19714439,
                                    0.09535613, 3.99125545])
    assert np.allclose(fm.parameters, parameters_expected, atol=1e-5)


def test_cube_fitting_backend():
    np.random.seed(42)

    SIGMA = 0.1  # noise in data
    TOL   = 0.4  # test tolerance

    # Flux cube oriented as in JWST data. To build a Spectrum1D
    # instance with this, one need to transpose it so the spectral
    # axis direction corresponds to the last index.
    flux_cube = np.zeros((SPECTRUM_SIZE, IMAGE_SIZE, IMAGE_SIZE))

    # Generate list of all spaxels to be fitted
    _spx = [[(x, y) for x in range(IMAGE_SIZE)] for y in range(IMAGE_SIZE)]
    spaxels = [item for sublist in _spx for item in sublist]

    # Fill cube spaxels with spectra that differ from
    # each other only by their noise component.
    x, _ = build_spectrum()
    for spx in spaxels:
        flux_cube[:,spx[0],spx[1]] = build_spectrum(sigma=SIGMA)[1]

    # Transpose so it can be packed in a Spectrum1D instance.
    flux_cube = flux_cube.transpose(1, 2, 0)

    spectrum = Spectrum1D(flux=flux_cube*u.Jy, spectral_axis=x*u.um)

    # Initial model for fit.
    g1f = models.Gaussian1D(0.7*u.Jy, 4.65*u.um, 0.3*u.um, name='g1')
    g2f = models.Gaussian1D(2.0*u.Jy, 5.55*u.um, 0.3*u.um, name='g2')
    g3f = models.Gaussian1D(-2.*u.Jy, 8.15*u.um, 0.2*u.um, name='g3')
    zero_level = models.Const1D(1.*u.Jy, name='const1d')

    model_list = [g1f, g2f, g3f, zero_level]
    expression = "g1 + g2 + g3 + const1d"

    # Fit to all spaxels.
    fitted_parameters, fitted_spectrum = fb.fit_model_to_spectrum(
        spectrum, model_list, expression)

    # Check that parameter results are formatted as expected.
    assert type(fitted_parameters) == list
    assert len(fitted_parameters) == 10

    assert type(fitted_parameters[0]) == u.Quantity
    assert fitted_parameters[0].unit == u.Jy
    assert fitted_parameters[0].shape == (IMAGE_SIZE, IMAGE_SIZE)

    assert type(fitted_parameters[1]) == u.Quantity
    assert fitted_parameters[1].unit == u.um
    assert fitted_parameters[1].shape == (IMAGE_SIZE, IMAGE_SIZE)

    # Check that spectrum result is formatted as expected.
    assert type(fitted_spectrum) == Spectrum1D
    assert len(fitted_spectrum.shape) == 3
    assert fitted_spectrum.shape == (IMAGE_SIZE, IMAGE_SIZE, SPECTRUM_SIZE)
    assert fitted_spectrum.flux.unit == u.Jy

    # The important point here isn't to check the accuracy of the
    # fit, which was already tested elsewhere. We are mostly
    # interested here in checking the correctness of the data
    # packaging into the output products.

    assert np.allclose(fitted_parameters[0].value,  1.,  atol=TOL)
    assert np.allclose(fitted_parameters[3].value,  2.5, atol=TOL)
    assert np.allclose(fitted_parameters[6].value, -1.7, atol=TOL)

    assert np.allclose(fitted_parameters[1].value, 4.6, atol=TOL)
    assert np.allclose(fitted_parameters[4].value, 5.5, atol=TOL)
    assert np.allclose(fitted_parameters[7].value, 8.2, atol=TOL)

    assert np.allclose(fitted_parameters[2].value, 0.2, atol=TOL)
    assert np.allclose(fitted_parameters[5].value, 0.1, atol=TOL)
    assert np.allclose(fitted_parameters[8].value, 0.1, atol=TOL)

    assert np.allclose(fitted_parameters[9].value, 4.0, atol=TOL)
