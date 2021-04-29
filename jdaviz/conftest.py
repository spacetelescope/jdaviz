# This file is used to configure the behavior of pytest when using the Astropy
# test infrastructure. It needs to live inside the package in order for it to
# get picked up when running the tests inside an interpreter using
# packagename.test

import os
import pytest

from astropy.wcs import WCS


@pytest.fixture
def spectral_cube_wcs(request):
    # A simple spectral cube WCS used by some tests
    wcs = WCS(naxis=3)
    wcs.wcs.ctype = 'RA---TAN', 'DEC--TAN', 'FREQ'
    wcs.wcs.set()
    return wcs


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
