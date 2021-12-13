# This file is used to configure the behavior of pytest when using the Astropy
# test infrastructure. It needs to live inside the package in order for it to
# get picked up when running the tests inside an interpreter using
# packagename.test

import numpy as np
import pytest
from astropy import units as u
from astropy.nddata import StdDevUncertainty
from astropy.wcs import WCS
from specutils import Spectrum1D

from jdaviz import __version__, Cubeviz, Imviz, Mosviz, Specviz, Specviz2d

SPECTRUM_SIZE = 10  # length of spectrum


@pytest.fixture
def cubeviz_app():
    return Cubeviz()


@pytest.fixture
def imviz_app():
    return Imviz()


@pytest.fixture
def mosviz_app():
    return Mosviz()


@pytest.fixture
def specviz_app():
    return Specviz()


@pytest.fixture
def specviz2d_app():
    return Specviz2d()


@pytest.fixture
def spectral_cube_wcs(request):
    # A simple spectral cube WCS used by some tests
    wcs = WCS(naxis=3)
    wcs.wcs.ctype = 'RA---TAN', 'DEC--TAN', 'FREQ'
    wcs.wcs.set()
    return wcs


@pytest.fixture
def spectrum1d_cube_wcs(request):
    # A simple spectrum1D WCS used by some tests
    wcs = WCS(naxis=3)
    wcs.wcs.ctype = 'RA---TAN', 'DEC--TAN', 'WAVE-LOG'
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
def spectrum1d_cube():
    flux = np.arange(16).reshape([2, 2, 4]) * u.Jy
    wcs_dict = {"CTYPE1": "RA---TAN", "CTYPE2": "DEC--TAN", "CTYPE3": "WAVE-LOG",
                "CRVAL1": 205, "CRVAL2": 27, "CRVAL3": 4.622e-7,
                "CDELT1": -0.0001, "CDELT2": 0.0001, "CDELT3": 8e-11,
                "CRPIX1": 0, "CRPIX2": 0, "CRPIX3": 0}
    w = WCS(wcs_dict)

    spec = Spectrum1D(flux=flux, wcs=w)

    return spec


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
    PYTEST_HEADER_MODULES['spectral-cube'] = 'spectral_cube'
    PYTEST_HEADER_MODULES['asteval'] = 'asteval'
    PYTEST_HEADER_MODULES['click'] = 'click'
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

# TODO: Need to handle warnings properly first before we can enable this. See
# https://github.com/spacetelescope/jdaviz/issues/478
# Uncomment the last two lines in this block to treat all DeprecationWarnings as
# exceptions.
# from astropy.tests.helper import enable_deprecations_as_exceptions  # noqa
# enable_deprecations_as_exceptions()
