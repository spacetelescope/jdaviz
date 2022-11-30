import astropy.modeling.models as models
import astropy.modeling.parameters as params
from astropy.nddata import StdDevUncertainty
import astropy.units as u
import numpy as np
import pytest

from specutils.spectra import Spectrum1D

from jdaviz.configs.default.plugins.model_fitting import fitting_backend as fb
from jdaviz.configs.default.plugins.model_fitting import initializers
from jdaviz.configs.default.plugins.model_fitting.model_fitting import ModelFitting

SPECTRUM_SIZE = 200  # length of spectrum


def build_spectrum(sigma=0.1):
    g1 = models.Gaussian1D(1, 4.6, 0.2)
    g2 = models.Gaussian1D(2.5, 5.5, 0.1)
    g3 = models.Gaussian1D(-1.7, 8.2, 0.1)

    x = np.linspace(0, 10, SPECTRUM_SIZE)
    y = g1(x) + g2(x) + g3(x)

    noise = np.random.normal(4., sigma, x.shape)

    return x, y + noise


def test_model_params():
    # expected model parameters:
    model_parameters = {"Gaussian1D": ["amplitude", "stddev", "mean"],
                        "Const1D": ["amplitude"],
                        "Linear1D": ["slope", "intercept"],
                        "Polynomial1D": ["c0", "c1"],
                        "PowerLaw1D": ["amplitude", "x_0", "alpha"],
                        "Lorentz1D": ["amplitude", "x_0", "fwhm"],
                        "Voigt1D": ["x_0", "amplitude_L", "fwhm_L", "fwhm_G"],
                        "BlackBody": ["temperature", "scale"],
                        }

    for model_name in initializers.MODELS.keys():
        if model_name not in model_parameters.keys():
            # this would be caught later by the assertion anyways,
            # but raising an error will be more clear that the
            # test needs to be updated rather than the code breaking
            raise ValueError(f"{model_name} not in test dictionary of expected parameters")
        expected_params = model_parameters.get(model_name, [])
        params = initializers.get_model_parameters(model_name)
        assert len(params) == len(expected_params)
        assert np.all([p in expected_params for p in params])


@pytest.mark.filterwarnings('ignore')
def test_model_ids(cubeviz_helper, spectral_cube_wcs):
    cubeviz_helper.load_data(Spectrum1D(flux=np.ones((3, 4, 5)) * u.nJy, wcs=spectral_cube_wcs),
                             data_label='test')
    plugin = ModelFitting(app=cubeviz_helper.app)
    plugin.dataset_selected = 'test[FLUX]'
    plugin.component_models = [{'id': 'valid_string_already_exists'}]
    plugin.comp_selected = 'Linear1D'

    with pytest.raises(
            ValueError,
            match="model component label 'valid_string_already_exists' already in use"):
        plugin.comp_label = 'valid_string_already_exists'
        plugin.vue_add_model({})

    with pytest.raises(
            ValueError,
            match="invalid model component label 'invalid-string'"):
        plugin.comp_label = 'invalid-string'
        plugin.vue_add_model({})


@pytest.mark.parametrize('unc', ('zeros', None))
def test_fitting_backend(unc):
    np.random.seed(42)

    x, y = build_spectrum()

    # The uncertainty array of all zero should be ignored when fitting
    if unc == "zeros":
        uncertainties = StdDevUncertainty(np.zeros(y.shape)*u.Jy)
    elif unc is None:
        uncertainties = None
    spectrum = Spectrum1D(flux=y*u.Jy, spectral_axis=x*u.um, uncertainty=uncertainties)

    g1f = models.Gaussian1D(0.7*u.Jy, 4.65*u.um, 0.3*u.um, name='g1')
    g2f = models.Gaussian1D(2.0*u.Jy, 5.55*u.um, 0.3*u.um, name='g2')
    g3f = models.Gaussian1D(-2.*u.Jy, 8.15*u.um, 0.2*u.um, name='g3')
    zero_level = models.Const1D(1.*u.Jy, name='const1d')

    model_list = [g1f, g2f, g3f, zero_level]
    expression = "g1 + g2 + g3 + const1d"

    # Returns the initial model
    fm, fitted_spectrum = fb.fit_model_to_spectrum(spectrum, model_list, expression,
                                                   run_fitter=False)

    parameters_expected = np.array([0.7, 4.65, 0.3, 2., 5.55, 0.3, -2.,
                                    8.15, 0.2, 1.])
    assert np.allclose(fm.parameters, parameters_expected, atol=1e-5)

    # Returns the fitted model
    fm, fitted_spectrum = fb.fit_model_to_spectrum(spectrum, model_list, expression,
                                                   run_fitter=True)

    parameters_expected = np.array([1.0104705, 4.58956282, 0.19590464, 2.39892026,
                                    5.49867754, 0.10834472, -1.66902953, 8.19714439,
                                    0.09535613, 3.99125545])
    assert np.allclose(fm.parameters, parameters_expected, atol=1e-5)


# When pytest turns warnings into errors, this silently fails with
# len(fitted_parameters) == 0
@pytest.mark.filterwarnings('ignore')
@pytest.mark.parametrize('unc', ('zeros', None))
def test_cube_fitting_backend(unc):
    np.random.seed(42)

    SIGMA = 0.1  # noise in data
    TOL = 0.4  # test tolerance
    IMAGE_SIZE_X = 15
    IMAGE_SIZE_Y = 14

    # Flux cube oriented as in JWST data. To build a Spectrum1D
    # instance with this, one need to transpose it so the spectral
    # axis direction corresponds to the last index.
    flux_cube = np.zeros((SPECTRUM_SIZE, IMAGE_SIZE_X, IMAGE_SIZE_Y))

    # Generate list of all spaxels to be fitted
    _spx = [[(x, y) for x in range(IMAGE_SIZE_X)] for y in range(IMAGE_SIZE_Y)]
    spaxels = [item for sublist in _spx for item in sublist]

    # Fill cube spaxels with spectra that differ from
    # each other only by their noise component.
    x, _ = build_spectrum()
    for spx in spaxels:
        flux_cube[:, spx[0], spx[1]] = build_spectrum(sigma=SIGMA)[1]

    # Transpose so it can be packed in a Spectrum1D instance.
    flux_cube = flux_cube.transpose(1, 2, 0)

    # Mask part of the spectral axis to later ensure that it gets propagated through:
    mask = np.zeros_like(flux_cube).astype(bool)
    mask[..., :SPECTRUM_SIZE // 10] = True

    # The uncertainty array of all zero should be ignored when fitting
    if unc == "zeros":
        uncertainties = StdDevUncertainty(np.zeros(flux_cube.shape)*u.Jy)
    elif unc is None:
        uncertainties = None

    spectrum = Spectrum1D(flux=flux_cube*u.Jy, spectral_axis=x*u.um,
                          uncertainty=uncertainties, mask=mask)

    # Initial model for fit.
    g1f = models.Gaussian1D(0.7*u.Jy, 4.65*u.um, 0.3*u.um, name='g1')
    g2f = models.Gaussian1D(2.0*u.Jy, 5.55*u.um, 0.3*u.um, name='g2')
    g3f = models.Gaussian1D(-2.*u.Jy, 8.15*u.um, 0.2*u.um, name='g3')
    zero_level = models.Const1D(1.*u.Jy, name='const1d')

    model_list = [g1f, g2f, g3f, zero_level]
    expression = "g1 + g2 + g3 + const1d"

    n_cpu = None
    # n_cpu = 1  # NOTE: UNCOMMENT TO DEBUG LOCALLY, AS NEEDED

    # Fit to all spaxels.
    fitted_parameters, fitted_spectrum = fb.fit_model_to_spectrum(
        spectrum, model_list, expression, n_cpu=n_cpu)

    # Check that parameter results are formatted as expected.
    assert type(fitted_parameters) == list
    assert len(fitted_parameters) == IMAGE_SIZE_X * IMAGE_SIZE_Y

    for m in fitted_parameters:
        if m['x'] == 3 and m['y'] == 2:
            fitted_model = m['model']

    assert type(fitted_model[0].amplitude.value) == np.float64
    assert fitted_model[0].amplitude.unit == u.Jy

    assert type(fitted_model[0] == params.Parameter)
    assert type(fitted_model[0].mean.value) == np.float64
    assert fitted_model[0].mean.unit == u.um

    # Check that spectrum result is formatted as expected.
    assert type(fitted_spectrum) == Spectrum1D
    assert len(fitted_spectrum.shape) == 3
    assert fitted_spectrum.shape == (IMAGE_SIZE_X, IMAGE_SIZE_Y, SPECTRUM_SIZE)
    assert fitted_spectrum.flux.unit == u.Jy
    assert not np.all(fitted_spectrum.flux.value == 0)

    # The important point here isn't to check the accuracy of the
    # fit, which was already tested elsewhere. We are mostly
    # interested here in checking the correctness of the data
    # packaging into the output products.

    assert np.allclose(fitted_model[0].amplitude.value, 1.09, atol=TOL)
    assert np.allclose(fitted_model[1].amplitude.value, 2.4, atol=TOL)
    assert np.allclose(fitted_model[2].amplitude.value, -1.7, atol=TOL)

    assert np.allclose(fitted_model[0].mean.value, 4.6, atol=TOL)
    assert np.allclose(fitted_model[1].mean.value, 5.5, atol=TOL)
    assert np.allclose(fitted_model[2].mean.value, 8.2, atol=TOL)

    assert np.allclose(fitted_model[0].stddev.value, 0.2, atol=TOL)
    assert np.allclose(fitted_model[1].stddev.value, 0.1, atol=TOL)
    assert np.allclose(fitted_model[2].stddev.value, 0.1, atol=TOL)

    assert np.allclose(fitted_model[3].amplitude.value, 4.0, atol=TOL)
