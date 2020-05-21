import astropy.modeling.models as models
import astropy.units as u
import numpy as np
from specutils.spectra import Spectrum1D

from .. import fitting_backend as fb


def test_fitting_backend():
    np.random.seed(42)

    g1 = models.Gaussian1D(1, 4.6, 0.2)
    g2 = models.Gaussian1D(2.5, 5.5, 0.1)
    g3 = models.Gaussian1D(-1.7, 8.2, 0.1)
    x = np.linspace(0, 10, 200)
    y = g1(x) + g2(x) + g3(x) + np.random.normal(4., 0.1, x.shape)

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
