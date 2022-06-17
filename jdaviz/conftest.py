# This file is used to configure the behavior of pytest when using the Astropy
# test infrastructure. It needs to live inside the package in order for it to
# get picked up when running the tests inside an interpreter using
# packagename.test

import warnings
import numpy as np
import pytest
from astropy import units as u
from astropy.nddata import CCDData, StdDevUncertainty
from astropy.wcs import WCS
from specutils import Spectrum1D, SpectrumCollection

from jdaviz import __version__, Cubeviz, Imviz, Mosviz, Specviz, Specviz2d

SPECTRUM_SIZE = 10  # length of spectrum


@pytest.fixture
def cubeviz_helper():
    return Cubeviz()


@pytest.fixture
def imviz_helper():
    return Imviz()


@pytest.fixture
def mosviz_helper():
    return Mosviz()


@pytest.fixture
def specviz_helper():
    return Specviz()


@pytest.fixture
def specviz2d_helper():
    return Specviz2d()


@pytest.fixture
def image_2d_wcs(request):
    return WCS({'CTYPE1': 'RA---TAN', 'CUNIT1': 'deg', 'CDELT1': -0.0002777777778,
                'CRPIX1': 1, 'CRVAL1': 337.5202808,
                'CTYPE2': 'DEC--TAN', 'CUNIT2': 'deg', 'CDELT2': 0.0002777777778,
                'CRPIX2': 1, 'CRVAL2': -20.833333059999998})


@pytest.fixture
def spectral_cube_wcs(request):
    # A simple spectral cube WCS used by some tests
    wcs = WCS(naxis=3)
    wcs.wcs.ctype = 'FREQ', 'DEC--TAN', 'RA---TAN'
    wcs.wcs.set()
    return wcs


@pytest.fixture
def spectrum1d_cube_wcs(request):
    # A simple spectrum1D WCS used by some tests
    wcs = WCS(naxis=3)
    wcs.wcs.ctype = 'WAVE-LOG', 'DEC--TAN', 'RA---TAN'
    wcs.wcs.set()
    return wcs


@pytest.fixture
def spectrum1d():
    np.random.seed(42)

    spec_axis = np.linspace(6000, 8000, SPECTRUM_SIZE) * u.AA
    flux = (np.random.randn(len(spec_axis.value)) +
            10*np.exp(-0.001*(spec_axis.value-6563)**2) +
            spec_axis.value/500) * u.Jy
    uncertainty = StdDevUncertainty(np.abs(np.random.randn(len(spec_axis.value))) * u.Jy)

    return Spectrum1D(spectral_axis=spec_axis, flux=flux, uncertainty=uncertainty)


@pytest.fixture
def spectrum_collection(spectrum1d):
    sc = [spectrum1d] * 5

    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        result = SpectrumCollection.from_spectra(sc)
    return result


@pytest.fixture
def spectrum1d_cube():
    flux = np.arange(16).reshape((2, 2, 4)) * u.Jy
    wcs_dict = {"CTYPE1": "RA---TAN", "CTYPE2": "DEC--TAN", "CTYPE3": "WAVE-LOG",
                "CRVAL1": 205, "CRVAL2": 27, "CRVAL3": 4.622e-7,
                "CDELT1": -0.0001, "CDELT2": 0.0001, "CDELT3": 8e-11,
                "CRPIX1": 0, "CRPIX2": 0, "CRPIX3": 0}
    w = WCS(wcs_dict)

    return Spectrum1D(flux=flux, wcs=w)


@pytest.fixture
def mos_spectrum1d():
    '''
    A specially defined Spectrum1d that matches the corresponding spectrum2d below.

    TODO: this fixture should be replaced by the global spectrum1d fixture defined in
    jdaviz/conftest.py AFTER reforming the spectrum2d fixture below to match the
    global spectrum1d fixture.

    Unless linking the two is required, try to use the global spectrum1d fixture.
    '''
    spec_axis = np.linspace(6000, 8000, 1024) * u.AA
    np.random.seed(42)
    flux = (np.random.randn(len(spec_axis.value)) +
            10*np.exp(-0.001*(spec_axis.value-6563)**2) +
            spec_axis.value/500) * u.Jy

    return Spectrum1D(spectral_axis=spec_axis, flux=flux)


@pytest.fixture
def mos_spectrum2d():
    '''
    A specially defined 2D (spatial) Spectrum1D whose wavelength range matches the
    mos-specific 1D spectrum.

    TODO: This should be reformed to match the global Spectrum1D defined above so that we may
    deprecate the mos-specific spectrum1d.
    '''
    header = {
        'WCSAXES': 2,
        'CRPIX1': 0.0, 'CRPIX2': 1024.5,
        'CDELT1': 1E-06, 'CDELT2': 2.9256727777778E-05,
        'CUNIT1': 'm', 'CUNIT2': 'deg',
        'CTYPE1': 'WAVE', 'CTYPE2': 'OFFSET',
        'CRVAL1': 0.0, 'CRVAL2': 5.0,
        'RADESYS': 'ICRS', 'SPECSYS': 'BARYCENT'}
    wcs = WCS(header)
    np.random.seed(42)
    data = np.random.sample((1024, 15)) * u.one
    return Spectrum1D(data, wcs=wcs, meta=header)


@pytest.fixture
def mos_image():
    header = {
        'WCSAXES': 2,
        'CRPIX1': 937.0, 'CRPIX2': 696.0,
        'CDELT1': -1.5182221158397e-05, 'CDELT2': 1.5182221158397e-05,
        'CUNIT1': 'deg', 'CUNIT2': 'deg',
        'CTYPE1': 'RA---TAN', 'CTYPE2': 'DEC--TAN',
        'CRVAL1': 5.0155198140981, 'CRVAL2': 5.002450989248,
        'LONPOLE': 180.0, 'LATPOLE': 5.002450989248,
        'DATEREF': '1858-11-17', 'MJDREFI': 0.0, 'MJDREFF': 0.0,
        'RADESYS': 'ICRS'}
    wcs = WCS(header)
    np.random.seed(42)
    data = np.random.sample((55, 55))
    return CCDData(data, wcs=wcs, unit='Jy', meta=header)


try:
    from pytest_astropy_header.display import PYTEST_HEADER_MODULES, TESTED_VERSIONS
except ImportError:
    PYTEST_HEADER_MODULES = {}
    TESTED_VERSIONS = {}


def pytest_configure(config):
    PYTEST_HEADER_MODULES['astropy'] = 'astropy'
    PYTEST_HEADER_MODULES['pyyaml'] = 'yaml'
    PYTEST_HEADER_MODULES['scikit-image'] = 'skimage'
    PYTEST_HEADER_MODULES['specutils'] = 'specutils'
    PYTEST_HEADER_MODULES['asteval'] = 'asteval'
    PYTEST_HEADER_MODULES['echo'] = 'echo'
    PYTEST_HEADER_MODULES['idna'] = 'idna'
    PYTEST_HEADER_MODULES['traitlets'] = 'traitlets'
    PYTEST_HEADER_MODULES['bqplot'] = 'bqplot'
    PYTEST_HEADER_MODULES['bqplot-image-gl'] = 'bqplot_image_gl'
    PYTEST_HEADER_MODULES['glue-core'] = 'glue'
    PYTEST_HEADER_MODULES['glue-jupyter'] = 'glue_jupyter'
    PYTEST_HEADER_MODULES['glue-astronomy'] = 'glue_astronomy'
    PYTEST_HEADER_MODULES['ipyvue'] = 'ipyvue'
    PYTEST_HEADER_MODULES['ipyvuetify'] = 'ipyvuetify'
    PYTEST_HEADER_MODULES['ipysplitpanes'] = 'ipysplitpanes'
    PYTEST_HEADER_MODULES['ipygoldenlayout'] = 'ipygoldenlayout'
    PYTEST_HEADER_MODULES['voila'] = 'voila'
    PYTEST_HEADER_MODULES['vispy'] = 'vispy'
    PYTEST_HEADER_MODULES['gwcs'] = 'gwcs'
    PYTEST_HEADER_MODULES['asdf'] = 'asdf'

    TESTED_VERSIONS['jdaviz'] = __version__
