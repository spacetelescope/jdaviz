import warnings

import numpy as np
import pytest
from astropy import units as u
from astropy.io import fits
from astropy.io.registry.base import IORegistryError
from astropy.modeling import models, parameters as params
from astropy.nddata import StdDevUncertainty
from astropy.tests.helper import assert_quantity_allclose
from astropy.wcs import WCS
from numpy.testing import assert_allclose, assert_array_equal
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


@pytest.mark.filterwarnings(r"ignore:Model is linear in parameters.*")
def test_parameter_retrieval(cubeviz_helper, spectral_cube_wcs):
    flux = np.ones((3, 4, 5))
    flux[2, 2, :] = [1, 2, 3, 4, 5]
    cubeviz_helper.load_data(Spectrum1D(flux=flux * u.nJy, wcs=spectral_cube_wcs),
                             data_label='test')
    plugin = cubeviz_helper.plugins["Model Fitting"]
    plugin.create_model_component("Linear1D", "L")
    plugin.cube_fit = True
    plugin.calculate_fit()

    params = cubeviz_helper.get_model_parameters()
    slope_res = np.zeros((4, 3))
    slope_res[2, 2] = 1.0
    slope_res = slope_res * u.nJy / u.Hz
    intercept_res = np.ones((4, 3))
    intercept_res[2, 2] = 0
    intercept_res = intercept_res * u.nJy
    assert_quantity_allclose(params['cube-fit model']['slope'], slope_res,
                             atol=1e-10 * u.nJy / u.Hz)
    assert_quantity_allclose(params['cube-fit model']['intercept'], intercept_res,
                             atol=1e-10 * u.nJy)


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
    assert_allclose(fm.parameters, parameters_expected, atol=1e-5)

    # Returns the fitted model
    fm, fitted_spectrum = fb.fit_model_to_spectrum(spectrum, model_list, expression,
                                                   run_fitter=True)

    parameters_expected = np.array([1.0104705, 4.58956282, 0.19590464, 2.39892026,
                                    5.49867754, 0.10834472, -1.66902953, 8.19714439,
                                    0.09535613, 3.99125545])
    assert_allclose(fm.parameters, parameters_expected, atol=1e-5)


@pytest.mark.parametrize('unc', ('zeros', None))
def test_cube_fitting_backend(cubeviz_helper, unc, tmp_path):
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
    flux_cube = flux_cube.transpose(1, 2, 0)  # (15, 14, 200)
    cube_wcs = WCS({
        'WCSAXES': 3, 'RADESYS': 'ICRS', 'EQUINOX': 2000.0,
        'CRPIX3': 38.0, 'CRPIX2': 38.0, 'CRPIX1': 1.0,
        'CRVAL3': 205.4384, 'CRVAL2': 27.004754, 'CRVAL1': 0.0,
        'CDELT3': 0.01, 'CDELT2': 0.01, 'CDELT1': 0.05,
        'CUNIT3': 'deg', 'CUNIT2': 'deg', 'CUNIT1': 'um',
        'CTYPE3': 'RA---TAN', 'CTYPE2': 'DEC--TAN', 'CTYPE1': 'WAVE'})

    # Mask part of the spectral axis to later ensure that it gets propagated through:
    mask = np.zeros_like(flux_cube).astype(bool)
    mask[..., :SPECTRUM_SIZE // 10] = True

    # The uncertainty array of all zero should be ignored when fitting
    if unc == "zeros":
        uncertainties = StdDevUncertainty(np.zeros(flux_cube.shape)*u.Jy)
    elif unc is None:
        uncertainties = None

    spectrum = Spectrum1D(flux=flux_cube*u.Jy, wcs=cube_wcs,
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
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=r"The fit may be unsuccessful.*")
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

    assert_allclose(fitted_model[0].amplitude.value, 1.09, atol=TOL)
    assert_allclose(fitted_model[1].amplitude.value, 2.4, atol=TOL)
    assert_allclose(fitted_model[2].amplitude.value, -1.7, atol=TOL)

    assert_allclose(fitted_model[0].mean.value, 4.6, atol=TOL)
    assert_allclose(fitted_model[1].mean.value, 5.5, atol=TOL)
    assert_allclose(fitted_model[2].mean.value, 8.2, atol=TOL)

    assert_allclose(fitted_model[0].stddev.value, 0.2, atol=TOL)
    assert_allclose(fitted_model[1].stddev.value, 0.1, atol=TOL)
    assert_allclose(fitted_model[2].stddev.value, 0.1, atol=TOL)

    assert_allclose(fitted_model[3].amplitude.value, 4.0, atol=TOL)

    # Check that the fitted spectrum is masked correctly:
    assert_array_equal(fitted_spectrum.mask, mask)

    # Check I/O roundtrip.
    out_fn = tmp_path / "fitted_cube.fits"
    fitted_spectrum.write(out_fn, format="jdaviz-cube", overwrite=True)
    flux_unit_str = fitted_spectrum.flux.unit.to_string(format="fits")
    coo_expected = fitted_spectrum.wcs.pixel_to_world(1, 0, 2)
    with fits.open(out_fn) as pf:
        assert len(pf) == 3
        assert pf[0].name == "PRIMARY"
        assert pf[1].name == "SCI"
        assert pf[1].header["BUNIT"] == flux_unit_str
        assert_allclose(pf[1].data, fitted_spectrum.flux.value)
        assert pf[2].name == "MASK"
        assert_array_equal(pf[2].data, mask)
        w = WCS(pf[1].header)
        coo = w.pixel_to_world(1, 0, 2)
        assert_allclose(coo[0].value, coo_expected[0].value)  # SpectralCoord
        assert_allclose([coo[1].ra.deg, coo[1].dec.deg],
                        [coo_expected[1].ra.deg, coo_expected[1].dec.deg])

    # Our custom format is not registered to readers, just writers.
    # You can read it back in without custom read. See "Cubeviz roundtrip" below.
    with pytest.raises(IORegistryError, match="No reader defined"):
        Spectrum1D.read(out_fn, format="jdaviz-cube")

    # Check Cubeviz roundtrip.
    cubeviz_helper.load_data(out_fn)
    assert len(cubeviz_helper.app.data_collection) == 2
    data_sci = cubeviz_helper.app.data_collection["fitted_cube.fits[SCI]"]
    flux_sci = data_sci.get_component("flux")
    assert_allclose(flux_sci.data, fitted_spectrum.flux.value)
    assert flux_sci.units == flux_unit_str
    coo = data_sci.coords.pixel_to_world(1, 0, 2)
    assert_allclose(coo[0].value, coo_expected[0].value)  # SpectralCoord
    assert_allclose([coo[1].ra.deg, coo[1].dec.deg],
                    [coo_expected[1].ra.deg, coo_expected[1].dec.deg])
    data_mask = cubeviz_helper.app.data_collection["fitted_cube.fits[MASK]"]
    flux_mask = data_mask.get_component("flux")
    assert_array_equal(flux_mask.data, mask)


@pytest.mark.filterwarnings(r"ignore:Model is linear in parameters.*")
@pytest.mark.filterwarnings(r"ignore:The fit may be unsuccessful.*")
def test_results_table(specviz_helper, spectrum1d):
    data_label = 'test'
    specviz_helper.load_data(spectrum1d, data_label=data_label)

    mf = specviz_helper.plugins['Model Fitting']
    mf.create_model_component('Linear1D')

    mf.add_results.label = 'linear model'
    mf.calculate_fit(add_data=True)
    mf_table = mf.export_table()
    assert len(mf_table) == 1
    assert mf_table['equation'][-1] == 'L'
    assert mf_table.colnames == ['model', 'data_label', 'spectral_subset', 'equation',
                                 'L:slope_0', 'L:slope_0:unit',
                                 'L:slope_0:fixed', 'L:slope_0:std',
                                 'L:intercept_0', 'L:intercept_0:unit',
                                 'L:intercept_0:fixed', 'L:intercept_0:std']

    mf.create_model_component('Gaussian1D')
    mf.add_results.label = 'composite model'
    mf.calculate_fit(add_data=True)
    mf_table = mf.export_table()
    assert len(mf_table) == 2
    assert mf_table['equation'][-1] == 'L+G'
    assert mf_table.colnames == ['model', 'data_label', 'spectral_subset', 'equation',
                                 'L:slope_0', 'L:slope_0:unit',
                                 'L:slope_0:fixed', 'L:slope_0:std',
                                 'L:intercept_0', 'L:intercept_0:unit',
                                 'L:intercept_0:fixed', 'L:intercept_0:std',
                                 'G:amplitude_1', 'G:amplitude_1:unit',
                                 'G:amplitude_1:fixed', 'G:amplitude_1:std',
                                 'G:mean_1', 'G:mean_1:unit',
                                 'G:mean_1:fixed', 'G:mean_1:std',
                                 'G:stddev_1', 'G:stddev_1:unit',
                                 'G:stddev_1:fixed', 'G:stddev_1:std']


def test_equation_validation(specviz_helper, spectrum1d):
    data_label = 'test'
    specviz_helper.load_data(spectrum1d, data_label=data_label)

    mf = specviz_helper.plugins['Model Fitting']
    mf.create_model_component('Const1D')
    mf.create_model_component('Linear1D')

    assert mf.equation == 'C+L'
    assert mf._obj.model_equation_invalid_msg == ''

    mf.equation = 'L+'
    assert mf._obj.model_equation_invalid_msg == 'incomplete equation.'

    mf.equation = 'L+C'
    assert mf._obj.model_equation_invalid_msg == ''

    mf.equation = 'L+CC'
    assert mf._obj.model_equation_invalid_msg == 'CC is not an existing model component.'

    mf.equation = 'L+CC+DD'
    assert mf._obj.model_equation_invalid_msg == 'CC, DD are not existing model components.'

    mf.equation = ''
    assert mf._obj.model_equation_invalid_msg == 'model equation is required.'


@pytest.mark.filterwarnings(r"ignore:Model is linear in parameters.*")
@pytest.mark.filterwarnings(r"ignore:The fit may be unsuccessful.*")
def test_incompatible_units(specviz_helper, spectrum1d):
    data_label = 'test'
    specviz_helper.load_data(spectrum1d, data_label=data_label)

    mf = specviz_helper.plugins['Model Fitting']
    mf.create_model_component('Linear1D')

    mf.add_results.label = 'model native units'
    mf.calculate_fit(add_data=True)

    uc = specviz_helper.plugins['Unit Conversion']
    assert uc.spectral_unit.selected == "Angstrom"
    uc.spectral_unit = u.Hz

    assert 'L is currently disabled' in mf._obj.model_equation_invalid_msg
    mf.add_results.label = 'frequency units'
    with pytest.raises(ValueError, match=r"model equation is invalid.*"):
        mf.calculate_fit(add_data=True)

    mf.reestimate_model_parameters()
    assert mf._obj.model_equation_invalid_msg == ''
    mf.calculate_fit(add_data=True)
