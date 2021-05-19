# This file is used to configure the behavior of pytest when using the Astropy
# test infrastructure. It needs to live inside the package in order for it to
# get picked up when running the tests inside an interpreter using
# packagename.test

import os
import pytest

from astropy.wcs import WCS
from astropy import units as u
from astropy.nddata import StdDevUncertainty
import numpy as np
from specutils import Spectrum1D
from jdaviz.configs.specviz.helper import SpecViz


SPECTRUM_SIZE = 10  # length of spectrum


@pytest.fixture
def spectral_cube_wcs(request):
    # A simple spectral cube WCS used by some tests
    wcs = WCS(naxis=3)
    wcs.wcs.ctype = 'RA---TAN', 'DEC--TAN', 'FREQ'
    wcs.wcs.set()
    return wcs


@pytest.fixture
def specviz_app():
    return SpecViz()


@pytest.fixture
def spectrum1d():
    np.random.seed(42)

    spec_axis = np.linspace(6000, 8000, SPECTRUM_SIZE) * u.AA
    flux = (np.random.randn(len(spec_axis.value)) +
            10*np.exp(-0.001*(spec_axis.value-6563)**2) +
            spec_axis.value/500) * u.Jy
    uncertainty = StdDevUncertainty(np.abs(np.random.randn(len(spec_axis.value))) * u.Jy)

    return Spectrum1D(spectral_axis=spec_axis, flux=flux, uncertainty=uncertainty)


try:
    from pytest_astropy_header.display import PYTEST_HEADER_MODULES, TESTED_VERSIONS
except ImportError:
    PYTEST_HEADER_MODULES = {}
    TESTED_VERSIONS = {}


def pytest_configure(config):
    config.option.astropy_header = True

    # Customize the following lines to add/remove entries from the list of
    # packages for which version numbers are displayed when running the tests.
    PYTEST_HEADER_MODULES.pop('Pandas', None)
    PYTEST_HEADER_MODULES['scikit-image'] = 'skimage'

    from . import __version__
    packagename = os.path.basename(os.path.dirname(__file__))
    TESTED_VERSIONS[packagename] = __version__


# TODO: Need to handle warnings properly first before we can enable this. See
# https://github.com/spacetelescope/jdaviz/issues/478
# Uncomment the last two lines in this block to treat all DeprecationWarnings as
# exceptions.
# from astropy.tests.helper import enable_deprecations_as_exceptions  # noqa
# enable_deprecations_as_exceptions()
